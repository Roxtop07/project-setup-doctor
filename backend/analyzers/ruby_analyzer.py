from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class RubyAnalyzer(BaseAnalyzer):
    name = "ruby"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.RUBY not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_lockfile(root_path))
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_ruby_version(root_path))
        return issues

    def _check_lockfile(self, root_path: str) -> list[Issue]:
        if os.path.isfile(os.path.join(root_path, "Gemfile.lock")):
            return []
        return [
            Issue(
                id="ruby-no-lockfile",
                analyzer=self.name,
                severity=Severity.WARNING,
                message="Gemfile found but Gemfile.lock is missing. Run: bundle install",
            )
        ]

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("ruby") is not None:
            return []
        if not shutil.which("ruby"):
            return [
                Issue(
                    id="ruby-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Ruby runtime not found on PATH.",
                )
            ]
        return []

    def _check_ruby_version(self, root_path: str) -> list[Issue]:
        if os.path.isfile(os.path.join(root_path, ".ruby-version")):
            return []
        return [
            Issue(
                id="ruby-no-version-file",
                analyzer=self.name,
                severity=Severity.INFO,
                message="No .ruby-version file found. Consider adding one for version consistency.",
            )
        ]
