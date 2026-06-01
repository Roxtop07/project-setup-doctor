from __future__ import annotations

import logging
import os
from typing import Optional

from ai.config import AIConfig, resolve_ai_config
from ai.prompts import RESPONSE_SCHEMA, SYSTEM_PROMPT, build_user_prompt
from ai.providers import AIProvider, AIProviderError, build_provider
from ai.runtime import (
    AIRunMetadata,
    current_ai_config,
    current_ai_metadata,
    current_existing_issues,
    override_ai_provider,
)
from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, Severity

logger = logging.getLogger(__name__)

KEY_FILE_CANDIDATES = (
    "README.md",
    "readme.md",
    "package.json",
    "requirements.txt",
    "pyproject.toml",
    "Dockerfile",
    "docker-compose.yml",
    "docker-compose.yaml",
    ".env.example",
    ".env.sample",
)

MAX_KEY_FILE_BYTES = 2048
MAX_TREE_ENTRIES = 200
MAX_TOTAL_PAYLOAD = 12_000

DEFAULT_EXCLUDE_DIRS = frozenset({
    "node_modules",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
    "dist",
    "build",
    ".next",
    "target",
    ".pytest_cache",
    ".mypy_cache",
})


class AIAnalyzer(BaseAnalyzer):
    name = "ai"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        request_cfg = current_ai_config.get()
        config = resolve_ai_config(request_cfg)
        if config is None:
            return []

        try:
            provider = override_ai_provider.get() or build_provider(config)
        except AIProviderError as e:
            logger.warning("AI provider unavailable: %s", e)
            current_ai_metadata.set(AIRunMetadata(error=str(e)))
            return []

        existing_issues = current_existing_issues.get() or []
        try:
            user_prompt = self._build_prompt(root_path, project_info, existing_issues)
            response = await provider.complete(
                system=SYSTEM_PROMPT,
                user=user_prompt,
                schema=RESPONSE_SCHEMA,
            )
        except AIProviderError as e:
            logger.warning("AI provider call failed: %s", e)
            current_ai_metadata.set(
                AIRunMetadata(
                    error=str(e),
                    provider=config.provider,
                    model=config.effective_model(),
                )
            )
            return []
        except Exception as e:  # noqa: BLE001 — never break a scan
            logger.exception("Unexpected AI failure")
            current_ai_metadata.set(
                AIRunMetadata(
                    error=str(e),
                    provider=config.provider,
                    model=config.effective_model(),
                )
            )
            return []

        issues = self._parse_findings(response)
        current_ai_metadata.set(
            AIRunMetadata(
                score=_safe_float(response.get("ai_score")),
                summary=_safe_str(response.get("ai_summary")),
                model=config.effective_model(),
                provider=config.provider,
            )
        )
        return issues

    # -- prompt construction -------------------------------------------------

    def _build_prompt(
        self,
        root_path: str,
        project_info: ProjectInfo,
        existing_issues: list[Issue],
    ) -> str:
        summary = self._summarize_project(project_info)
        tree = self._summarize_tree(root_path)
        key_files = self._gather_key_files(root_path)
        issues_summary = self._summarize_issues(existing_issues)

        prompt = build_user_prompt(summary, tree, key_files, issues_summary)
        if len(prompt) > MAX_TOTAL_PAYLOAD:
            prompt = prompt[:MAX_TOTAL_PAYLOAD] + "\n[truncated]"
        return prompt

    @staticmethod
    def _summarize_project(info: ProjectInfo) -> str:
        types = ", ".join(t.value for t in info.types) or "unknown"
        flags = []
        for attr in (
            "has_package_json",
            "has_requirements_txt",
            "has_pyproject_toml",
            "has_dockerfile",
            "has_docker_compose",
            "has_env_file",
            "has_env_example",
            "has_readme",
            "has_gitignore",
        ):
            if getattr(info, attr, False):
                flags.append(attr.replace("has_", ""))
        frameworks = ", ".join(info.detected_frameworks) or "none"
        return (
            f"name: {info.name}\n"
            f"types: {types}\n"
            f"frameworks: {frameworks}\n"
            f"present: {', '.join(flags) or 'none'}"
        )

    @staticmethod
    def _summarize_tree(root_path: str) -> str:
        entries: list[str] = []
        for dirpath, dirnames, filenames in os.walk(root_path):
            dirnames[:] = [d for d in dirnames if d not in DEFAULT_EXCLUDE_DIRS]
            rel_dir = os.path.relpath(dirpath, root_path)
            if rel_dir == ".":
                rel_dir = ""
            for name in filenames:
                entry = os.path.join(rel_dir, name) if rel_dir else name
                entries.append(entry)
                if len(entries) >= MAX_TREE_ENTRIES:
                    entries.append("... (truncated)")
                    return "\n".join(entries)
        return "\n".join(entries) or "(empty)"

    @staticmethod
    def _gather_key_files(root_path: str) -> dict[str, str]:
        gathered: dict[str, str] = {}
        for candidate in KEY_FILE_CANDIDATES:
            path = os.path.join(root_path, candidate)
            if not os.path.isfile(path):
                continue
            try:
                with open(path, encoding="utf-8", errors="replace") as f:
                    content = f.read(MAX_KEY_FILE_BYTES + 1)
            except OSError:
                continue
            if len(content) > MAX_KEY_FILE_BYTES:
                content = content[:MAX_KEY_FILE_BYTES] + "\n[truncated]"
            gathered[candidate] = content
        return gathered

    @staticmethod
    def _summarize_issues(issues: list[Issue]) -> str:
        if not issues:
            return "(none)"
        # Cap to keep payload bounded.
        capped = issues[:40]
        lines = []
        for issue in capped:
            loc = ""
            if issue.file:
                loc = f" ({issue.file}"
                if issue.line:
                    loc += f":{issue.line}"
                loc += ")"
            lines.append(
                f"- [{issue.severity.value}] {issue.analyzer}: {issue.message}{loc}"
            )
        if len(issues) > len(capped):
            lines.append(f"... and {len(issues) - len(capped)} more")
        return "\n".join(lines)

    # -- parsing -------------------------------------------------------------

    @staticmethod
    def _parse_findings(payload: dict) -> list[Issue]:
        raw = payload.get("findings") or []
        if not isinstance(raw, list):
            return []
        issues: list[Issue] = []
        for idx, item in enumerate(raw):
            if not isinstance(item, dict):
                continue
            severity = _parse_severity(item.get("severity"))
            message = _safe_str(item.get("message"))
            if not message:
                continue
            file_value = item.get("file")
            line_value = item.get("line")
            issues.append(
                Issue(
                    id=f"ai-{idx + 1}",
                    analyzer="ai",
                    severity=severity,
                    message=message,
                    file=file_value if isinstance(file_value, str) and file_value else None,
                    line=line_value if isinstance(line_value, int) else None,
                )
            )
        return issues


def _parse_severity(value) -> Severity:
    if isinstance(value, str):
        try:
            return Severity(value.lower())
        except ValueError:
            pass
    return Severity.INFO


def _safe_str(value) -> Optional[str]:
    if isinstance(value, str) and value.strip():
        return value.strip()
    return None


def _safe_float(value) -> Optional[float]:
    if isinstance(value, (int, float)):
        return float(value)
    return None
