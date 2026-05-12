from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class CsharpAnalyzer(BaseAnalyzer):
    name = "csharp"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.CSHARP not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("dotnet") is not None:
            return []
        if not shutil.which("dotnet"):
            return [
                Issue(
                    id="csharp-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message=".NET SDK (dotnet) not found on PATH.",
                )
            ]
        return []

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
        for entry in ["bin/", "obj/", "*.user", "*.suo"]:
            if entry not in content:
                missing.append(entry)

        if not missing:
            return []

        return [
            Issue(
                id="csharp-gitignore-incomplete",
                analyzer=self.name,
                severity=Severity.WARNING,
                message=f".NET build artifacts not in .gitignore: {', '.join(missing)}",
                file=gitignore_path,
            )
        ]
