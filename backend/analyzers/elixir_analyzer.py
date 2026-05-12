from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class ElixirAnalyzer(BaseAnalyzer):
    name = "elixir"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.ELIXIR not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_lockfile(root_path))
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_lockfile(self, root_path: str) -> list[Issue]:
        if os.path.isfile(os.path.join(root_path, "mix.lock")):
            return []
        return [
            Issue(
                id="elixir-no-lockfile",
                analyzer=self.name,
                severity=Severity.WARNING,
                message="mix.exs found but mix.lock is missing. Run: mix deps.get",
            )
        ]

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("elixir") is not None:
            return []
        if not shutil.which("elixir"):
            return [
                Issue(
                    id="elixir-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Elixir runtime not found on PATH.",
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
        for entry in ["_build", "deps", "*.ez"]:
            if entry not in content:
                missing.append(entry)

        if not missing:
            return []

        return [
            Issue(
                id="elixir-gitignore-incomplete",
                analyzer=self.name,
                severity=Severity.WARNING,
                message=f"Elixir build artifacts not in .gitignore: {', '.join(missing)}",
                file=gitignore_path,
            )
        ]
