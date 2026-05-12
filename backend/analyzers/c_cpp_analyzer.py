from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class CCppAnalyzer(BaseAnalyzer):
    name = "c_cpp"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if ProjectType.C not in project_info.types and ProjectType.CPP not in project_info.types:
            return []

        issues: list[Issue] = []
        issues.extend(self._check_build_system(root_path))
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_build_system(self, root_path: str) -> list[Issue]:
        build_files = [
            "CMakeLists.txt", "Makefile", "makefile", "meson.build",
            "configure", "configure.ac", "CMakePresets.json",
        ]
        if any(os.path.isfile(os.path.join(root_path, f)) for f in build_files):
            return []
        return [
            Issue(
                id="c-no-build-system",
                analyzer=self.name,
                severity=Severity.INFO,
                message="C/C++ source files found but no build system (CMake, Makefile, Meson) detected.",
            )
        ]

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        has_gcc = project_info.runtime_versions.get("gcc") is not None
        has_gpp = project_info.runtime_versions.get("g++") is not None
        has_clang = shutil.which("clang") is not None

        if has_gcc or has_gpp or has_clang:
            return []

        return [
            Issue(
                id="c-compiler-missing",
                analyzer=self.name,
                severity=Severity.WARNING,
                message="No C/C++ compiler (gcc, g++, clang) found on PATH.",
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
        for entry in ["*.o", "*.so", "*.a", "build/"]:
            if entry not in content:
                missing.append(entry)

        if not missing:
            return []

        return [
            Issue(
                id="c-gitignore-incomplete",
                analyzer=self.name,
                severity=Severity.WARNING,
                message=f"C/C++ build artifacts not in .gitignore: {', '.join(missing)}",
                file=gitignore_path,
            )
        ]
