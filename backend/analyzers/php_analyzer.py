from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class PhpAnalyzer(BaseAnalyzer):
    name = "php"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.PHP not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_lockfile(root_path))
        issues.extend(self._check_vendor(root_path))
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_lockfile(self, root_path: str) -> list[Issue]:
        if os.path.isfile(os.path.join(root_path, "composer.lock")):
            return []
        return [
            Issue(
                id="php-no-lockfile",
                analyzer=self.name,
                severity=Severity.WARNING,
                message="composer.json found but composer.lock is missing. Run: composer install",
            )
        ]

    def _check_vendor(self, root_path: str) -> list[Issue]:
        if os.path.isdir(os.path.join(root_path, "vendor")):
            return []
        return [
            Issue(
                id="php-no-vendor",
                analyzer=self.name,
                severity=Severity.ERROR,
                message="composer.json has dependencies but vendor/ is missing. Run: composer install",
            )
        ]

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("php") is not None:
            return []
        if not shutil.which("php"):
            return [
                Issue(
                    id="php-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="PHP runtime not found on PATH.",
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

        if "vendor" not in content:
            return [
                Issue(
                    id="php-gitignore-vendor",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="vendor/ directory not in .gitignore.",
                    file=gitignore_path,
                )
            ]
        return []
