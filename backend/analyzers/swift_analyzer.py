from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class SwiftAnalyzer(BaseAnalyzer):
    name = "swift"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.SWIFT not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_resolved(root_path))
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_resolved(self, root_path: str) -> list[Issue]:
        resolved = os.path.join(root_path, "Package.resolved")
        if os.path.isfile(resolved):
            return []
        return [
            Issue(
                id="swift-no-resolved",
                analyzer=self.name,
                severity=Severity.INFO,
                message="Package.swift found but Package.resolved is missing. Run: swift package resolve",
            )
        ]

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("swift") is not None:
            return []
        if not shutil.which("swift"):
            return [
                Issue(
                    id="swift-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Swift compiler not found on PATH.",
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

        if ".build" not in content:
            return [
                Issue(
                    id="swift-gitignore-build",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Swift .build/ directory not in .gitignore.",
                    file=gitignore_path,
                )
            ]
        return []
