from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

from ai.config import AIConfig
from ai.runtime import (
    current_ai_config,
    current_ai_metadata,
    current_existing_issues,
)
from analyzers.registry import AnalyzerRegistry
from detectors.project_detector import ProjectDetector
from models.contracts import (
    AutoFix,
    AutoFixRequest,
    AutoFixResult,
    ProjectInfo,
    ScanRequest,
    ScanResult,
)
from scoring.scoring_engine import ScoringEngine

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_FIX_COMMANDS = frozenset({
    "npm install",
    "npm ci",
    "pip install -r requirements.txt",
    "python3 -m venv .venv",
})

MAX_FIX_FILE_SIZE = 64 * 1024


def _validate_root_path(root_path: str) -> str:
    resolved = os.path.realpath(root_path)
    if not os.path.isdir(resolved):
        raise HTTPException(status_code=400, detail=f"Not a directory: {root_path}")
    return resolved


def _safe_resolve_path(relative_path: str, root_path: str) -> str:
    if os.path.isabs(relative_path):
        resolved = os.path.realpath(relative_path)
    else:
        resolved = os.path.realpath(os.path.join(root_path, relative_path))
    root_resolved = os.path.realpath(root_path)
    if not resolved.startswith(root_resolved + os.sep) and resolved != root_resolved:
        raise ValueError(f"Path escapes project root: {relative_path}")
    return resolved


@router.post("/scan")
async def scan_project(req: ScanRequest) -> ScanResult:
    start = time.monotonic()
    
    try:
        root_path = _validate_root_path(req.root_path)
        detector = ProjectDetector(root_path)
        project_info = detector.detect()
    except Exception as e:
        logger.exception("Failed to initialize scan for %s", req.root_path)
        duration = (time.monotonic() - start) * 1000
        from models.contracts import HealthScore, Issue, ProjectInfo, ProjectType, Severity
        return ScanResult(
            project_info=ProjectInfo(
                types=[ProjectType.UNKNOWN], root_path=req.root_path, name="Unknown"
            ),
            issues=[
                Issue(
                    id="scan-init-error",
                    analyzer="system",
                    severity=Severity.ERROR,
                    message=f"Scan initialization failed: {str(e)}"
                )
            ],
            health_score=HealthScore(total=0.0, grade="F"),
            scan_duration_ms=round(duration, 1),
            timestamp=datetime.now(timezone.utc).isoformat(),
        )

    # Plumb AI config from the request into the request-scoped ContextVar.
    ai_cfg_token = None
    if req.ai_config is not None:
        ai_cfg_token = current_ai_config.set(
            AIConfig(
                provider=req.ai_config.provider,  # type: ignore[arg-type]
                api_key=req.ai_config.api_key,
                base_url=req.ai_config.base_url,
                model=req.ai_config.model,
                enabled=req.ai_config.enabled,
            )
        )
    meta_token = current_ai_metadata.set(None)

    requested_names = req.analyzers or AnalyzerRegistry.list_names()
    # Always run rule-based analyzers first so the AI analyzer can see them.
    rule_names = [n for n in requested_names if n != "ai"]
    ai_requested = "ai" in requested_names

    all_issues = []

    for name in rule_names:
        analyzer = AnalyzerRegistry.get(name)
        if analyzer is None:
            logger.warning("Unknown analyzer requested: %s", name)
            continue
        try:
            issues = await analyzer.analyze(root_path, project_info)
            all_issues.extend(issues)
        except Exception as e:
            logger.exception("Analyzer %s failed on %s", name, root_path)
            from models.contracts import Issue, Severity
            all_issues.append(
                Issue(
                    id=f"analyzer-error-{name}",
                    analyzer="system",
                    severity=Severity.WARNING,
                    message=f"Analyzer '{name}' failed: {str(e)}"
                )
            )

    issues_token = current_existing_issues.set(list(all_issues))
    try:
        if ai_requested:
            ai_analyzer = AnalyzerRegistry.get("ai")
            if ai_analyzer is not None:
                try:
                    ai_issues = await ai_analyzer.analyze(root_path, project_info)
                    all_issues.extend(ai_issues)
                except Exception as e:
                    logger.exception("AI analyzer failed on %s", root_path)
                    from models.contracts import Issue, Severity
                    all_issues.append(
                        Issue(
                            id="analyzer-error-ai",
                            analyzer="system",
                            severity=Severity.WARNING,
                            message=f"Analyzer 'ai' failed: {str(e)}",
                        )
                    )
    finally:
        current_existing_issues.reset(issues_token)

    ai_metadata = current_ai_metadata.get()
    ai_score_for_blend = ai_metadata.score if ai_metadata else None

    try:
        health_score = ScoringEngine.compute(
            project_info, all_issues, ai_score=ai_score_for_blend
        )
    except Exception as e:
        logger.exception("Failed to compute health score")
        from models.contracts import HealthScore
        health_score = HealthScore(total=0.0, grade="F")
        from models.contracts import Issue, Severity
        all_issues.append(
            Issue(
                id="scoring-error",
                analyzer="system",
                severity=Severity.ERROR,
                message=f"Failed to compute health score: {str(e)}"
            )
        )

    duration = (time.monotonic() - start) * 1000

    current_ai_metadata.reset(meta_token)
    if ai_cfg_token is not None:
        current_ai_config.reset(ai_cfg_token)

    return ScanResult(
        project_info=project_info,
        issues=all_issues,
        health_score=health_score,
        scan_duration_ms=round(duration, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
        ai_summary=ai_metadata.summary if ai_metadata else None,
        ai_score=ai_metadata.score if ai_metadata else None,
        ai_provider=ai_metadata.provider if ai_metadata else None,
        ai_model=ai_metadata.model if ai_metadata else None,
        ai_error=ai_metadata.error if ai_metadata else None,
    )


@router.post("/health-score")
async def health_score(req: ScanRequest) -> ScanResult:
    return await scan_project(req)


@router.post("/project-info")
async def project_info(req: ScanRequest) -> ProjectInfo:
    try:
        root_path = _validate_root_path(req.root_path)
        detector = ProjectDetector(root_path)
        return detector.detect()
    except Exception:
        logger.exception("Failed to get project info for %s", req.root_path)
        from models.contracts import ProjectInfo, ProjectType
        return ProjectInfo(types=[ProjectType.UNKNOWN], root_path=req.root_path, name="Unknown")


@router.post("/autofix")
async def autofix(req: AutoFixRequest) -> AutoFixResult:
    result = AutoFixResult()
    try:
        root_path = _validate_root_path(req.root_path)
    except Exception as e:
        logger.exception("Invalid root path for autofix: %s", req.root_path)
        for fix_id in req.fix_ids:
            result.failed.append({"id": fix_id, "error": str(e)})
        return result

    try:
        scan_req = ScanRequest(root_path=root_path)
        scan_result = await scan_project(scan_req)
    except Exception as e:
        logger.exception("Failed to run scan before autofix")
        for fix_id in req.fix_ids:
            result.failed.append({"id": fix_id, "error": f"Scan failed: {str(e)}"})
        return result

    fix_map: dict[str, AutoFix] = {}
    for issue in scan_result.issues:
        if issue.fix:
            fix_map[issue.fix.id] = issue.fix

    for fix_id in req.fix_ids:
        fix = fix_map.get(fix_id)
        if not fix:
            result.failed.append({"id": fix_id, "error": "Fix not found in current scan"})
            continue

        try:
            await _apply_fix(fix, root_path)
            result.applied.append(fix_id)
        except Exception as e:
            logger.exception("Fix %s failed", fix_id)
            result.failed.append({"id": fix_id, "error": str(e)})

    return result


async def _apply_fix(fix: AutoFix, root_path: str) -> None:
    if fix.file_create:
        path = _safe_resolve_path(fix.file_create["path"], root_path)
        content = fix.file_create["content"]
        if len(content) > MAX_FIX_FILE_SIZE:
            raise ValueError("Generated file exceeds size limit")
        parent = os.path.dirname(path)
        _safe_resolve_path(os.path.relpath(parent, root_path), root_path)
        os.makedirs(parent, exist_ok=True)
        with open(path, "w") as f:
            f.write(content)

    if fix.command:
        if fix.command not in ALLOWED_FIX_COMMANDS:
            raise ValueError(f"Command not in allowlist: {fix.command}")
        parts = fix.command.split()
        proc = await asyncio.create_subprocess_exec(
            *parts,
            cwd=root_path,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        _, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        if proc.returncode != 0:
            raise RuntimeError(f"Command exited {proc.returncode}: {stderr.decode().strip()[:500]}")
