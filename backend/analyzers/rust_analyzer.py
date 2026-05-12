from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class RustAnalyzer(BaseAnalyzer):
    name = "rust"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.RUST not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_cargo_lock(root_path))
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_cargo_lock(self, root_path: str) -> list[Issue]:
        if os.path.isfile(os.path.join(root_path, "Cargo.lock")):
            return []
        return [
            Issue(
                id="rust-no-lockfile",
                analyzer=self.name,
                severity=Severity.WARNING,
                message="Cargo.toml found but Cargo.lock is missing. Run: cargo generate-lockfile",
            )
        ]

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("rust") is not None:
            return []
        if not shutil.which("rustc"):
            return [
                Issue(
                    id="rust-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Rust compiler (rustc) not found on PATH. Install from https://rustup.rs",
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

        if "target" not in content:
            return [
                Issue(
                    id="rust-gitignore-target",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Rust target/ directory not in .gitignore.",
                    file=gitignore_path,
                )
            ]
        return []
