from __future__ import annotations

import asyncio
import logging
import os
import time
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException

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
    root_path = _validate_root_path(req.root_path)

    detector = ProjectDetector(root_path)
    project_info = detector.detect()

    analyzer_names = req.analyzers or AnalyzerRegistry.list_names()
    all_issues = []

    for name in analyzer_names:
        analyzer = AnalyzerRegistry.get(name)
        if analyzer is None:
            logger.warning("Unknown analyzer requested: %s", name)
            continue
        try:
            issues = await analyzer.analyze(root_path, project_info)
            all_issues.extend(issues)
        except Exception:
            logger.exception("Analyzer %s failed on %s", name, root_path)

    health_score = ScoringEngine.compute(project_info, all_issues)
    duration = (time.monotonic() - start) * 1000

    return ScanResult(
        project_info=project_info,
        issues=all_issues,
        health_score=health_score,
        scan_duration_ms=round(duration, 1),
        timestamp=datetime.now(timezone.utc).isoformat(),
    )


@router.post("/health-score")
async def health_score(req: ScanRequest) -> ScanResult:
    return await scan_project(req)


@router.post("/project-info")
async def project_info(req: ScanRequest) -> ProjectInfo:
    root_path = _validate_root_path(req.root_path)
    detector = ProjectDetector(root_path)
    return detector.detect()


@router.post("/autofix")
async def autofix(req: AutoFixRequest) -> AutoFixResult:
    root_path = _validate_root_path(req.root_path)
    result = AutoFixResult()

    scan_req = ScanRequest(root_path=root_path)
    scan_result = await scan_project(scan_req)

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
