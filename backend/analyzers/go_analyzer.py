from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class GoAnalyzer(BaseAnalyzer):
    name = "go"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.GO not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_go_sum(root_path))
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_go_sum(self, root_path: str) -> list[Issue]:
        if not os.path.isfile(os.path.join(root_path, "go.mod")):
            return []
        if os.path.isfile(os.path.join(root_path, "go.sum")):
            return []
        return [
            Issue(
                id="go-no-sum",
                analyzer=self.name,
                severity=Severity.WARNING,
                message="go.mod found but go.sum is missing. Run: go mod tidy",
            )
        ]

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("go") is not None:
            return []
        if not shutil.which("go"):
            return [
                Issue(
                    id="go-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Go compiler not found on PATH.",
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

        name = project_info.name
        if name not in content and "/bin/" not in content and "bin/" not in content:
            return [
                Issue(
                    id="go-gitignore-binary",
                    analyzer=self.name,
                    severity=Severity.INFO,
                    message="Go binary output may not be in .gitignore. Consider adding your binary name or /bin/.",
                    file=gitignore_path,
                )
            ]
        return []
