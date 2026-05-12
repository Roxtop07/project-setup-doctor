from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import AutoFix, Issue, ProjectInfo, ProjectType, Severity


class EplAnalyzer(BaseAnalyzer):
    name = "epl"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.EPL not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_eplang_dependency(root_path, project_info))
        issues.extend(self._check_epl_runtime(project_info))
        issues.extend(self._check_entry_point(root_path))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_eplang_dependency(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        deps_text = ""
        for fname in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]:
            p = os.path.join(root_path, fname)
            if os.path.isfile(p):
                try:
                    with open(p) as f:
                        deps_text += f.read().lower() + "\n"
                except OSError:
                    pass

        if "eplang" in deps_text:
            return []

        req_path = os.path.join(root_path, "requirements.txt")
        return [
            Issue(
                id="epl-missing-eplang",
                analyzer=self.name,
                severity=Severity.ERROR,
                message=".epl files found but eplang is not listed in dependencies. Run: pip install eplang",
                fix=AutoFix(
                    id="epl-install-eplang",
                    description="Add eplang to requirements.txt",
                    file_create={
                        "path": "requirements.txt",
                        "content": "eplang\n",
                    }
                    if not os.path.isfile(req_path)
                    else None,
                    command="pip install eplang"
                    if os.path.isfile(req_path)
                    else None,
                ),
            )
        ]

    def _check_epl_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        epl_version = project_info.runtime_versions.get("epl")
        if epl_version is not None:
            return []

        if not shutil.which("epl"):
            return [
                Issue(
                    id="epl-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="EPL CLI (epl) not found on PATH. Install with: pip install eplang",
                )
            ]
        return []

    def _check_entry_point(self, root_path: str) -> list[Issue]:
        if os.path.isfile(os.path.join(root_path, "main.epl")):
            return []

        return [
            Issue(
                id="epl-no-main",
                analyzer=self.name,
                severity=Severity.INFO,
                message="No main.epl entry point found in project root.",
            )
        ]

    def _check_gitignore(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if not project_info.has_gitignore:
            return []

        gitignore_path = os.path.join(root_path, ".gitignore")
        try:
            with open(gitignore_path) as f:
                content = f.read()
        except OSError:
            return []

        missing: list[str] = []
        for entry in ["__eplcache__", "*.eplc", "deploy/"]:
            if entry not in content:
                missing.append(entry)

        if not missing:
            return []

        return [
            Issue(
                id="epl-gitignore-incomplete",
                analyzer=self.name,
                severity=Severity.WARNING,
                message=f"EPL build artifacts not in .gitignore: {', '.join(missing)}",
                file=gitignore_path,
            )
        ]
