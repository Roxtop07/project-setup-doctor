from __future__ import annotations

import json
import os
import re

from analyzers.base import BaseAnalyzer
from models.contracts import AutoFix, Issue, ProjectInfo, Severity


class DependencyAnalyzer(BaseAnalyzer):
    name = "dependencies"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        issues: list[Issue] = []

        if project_info.has_package_json:
            issues.extend(self._analyze_npm(root_path))

        if project_info.has_requirements_txt:
            issues.extend(self._analyze_pip_requirements(root_path))

        if project_info.has_pyproject_toml:
            issues.extend(self._analyze_pyproject(root_path))

        return issues

    def _analyze_npm(self, root_path: str) -> list[Issue]:
        issues: list[Issue] = []
        pkg_path = os.path.join(root_path, "package.json")

        try:
            with open(pkg_path) as f:
                pkg = json.load(f)
        except (OSError, json.JSONDecodeError):
            return issues

        deps = {**pkg.get("dependencies", {}), **pkg.get("devDependencies", {})}

        node_modules = os.path.join(root_path, "node_modules")
        if deps and not os.path.isdir(node_modules):
            issues.append(
                Issue(
                    id="npm-not-installed",
                    analyzer=self.name,
                    severity=Severity.ERROR,
                    message="package.json has dependencies but node_modules/ is missing. Run npm install.",
                    file=pkg_path,
                    fix=AutoFix(
                        id="npm-install",
                        description="Run npm install",
                        command="npm install",
                    ),
                )
            )

        lock_file = os.path.join(root_path, "package-lock.json")
        yarn_lock = os.path.join(root_path, "yarn.lock")
        pnpm_lock = os.path.join(root_path, "pnpm-lock.yaml")
        has_lock = any(os.path.isfile(f) for f in [lock_file, yarn_lock, pnpm_lock])

        if deps and not has_lock:
            issues.append(
                Issue(
                    id="npm-no-lockfile",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="No lockfile (package-lock.json, yarn.lock, or pnpm-lock.yaml) found. Builds may not be reproducible.",
                    file=pkg_path,
                )
            )

        for name, version in deps.items():
            ver = str(version).lstrip("^~>=<")
            if ver == "*" or ver == "latest":
                issues.append(
                    Issue(
                        id=f"npm-unpinned-{name}",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message=f'"{name}" uses unpinned version "{version}". Pin to a specific range.',
                        file=pkg_path,
                    )
                )

        if "dependencies" in pkg and "devDependencies" in pkg:
            overlap = set(pkg["dependencies"]) & set(pkg["devDependencies"])
            for name in sorted(overlap):
                issues.append(
                    Issue(
                        id=f"npm-duplicate-{name}",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message=f'"{name}" appears in both dependencies and devDependencies.',
                        file=pkg_path,
                    )
                )

        return issues

    def _analyze_pip_requirements(self, root_path: str) -> list[Issue]:
        issues: list[Issue] = []
        req_path = os.path.join(root_path, "requirements.txt")

        try:
            with open(req_path) as f:
                lines = f.readlines()
        except OSError:
            return issues

        seen: dict[str, int] = {}

        for i, line in enumerate(lines, 1):
            line = line.strip()
            if not line or line.startswith("#") or line.startswith("-"):
                continue

            match = re.match(r"^([a-zA-Z0-9_-]+)", line)
            if not match:
                continue

            pkg_name = match.group(1).lower()

            if pkg_name in seen:
                issues.append(
                    Issue(
                        id=f"pip-duplicate-{pkg_name}",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message=f'Duplicate package "{pkg_name}" (lines {seen[pkg_name]} and {i}).',
                        file=req_path,
                        line=i,
                    )
                )
            seen[pkg_name] = i

            if "==" not in line and ">=" not in line and "<=" not in line:
                issues.append(
                    Issue(
                        id=f"pip-unpinned-{pkg_name}",
                        analyzer=self.name,
                        severity=Severity.INFO,
                        message=f'"{pkg_name}" has no version constraint. Consider pinning.',
                        file=req_path,
                        line=i,
                    )
                )

        venv_path = os.path.join(root_path, ".venv")
        venv_path2 = os.path.join(root_path, "venv")
        if lines and not os.path.isdir(venv_path) and not os.path.isdir(venv_path2):
            issues.append(
                Issue(
                    id="pip-no-venv",
                    analyzer=self.name,
                    severity=Severity.INFO,
                    message="No virtual environment (.venv or venv) found. Consider creating one.",
                    fix=AutoFix(
                        id="create-venv",
                        description="Create Python virtual environment",
                        command="python3 -m venv .venv",
                    ),
                )
            )

        return issues

    def _analyze_pyproject(self, root_path: str) -> list[Issue]:
        issues: list[Issue] = []
        pyproject_path = os.path.join(root_path, "pyproject.toml")

        try:
            with open(pyproject_path) as f:
                content = f.read()
        except OSError:
            return issues

        if "[project]" not in content and "[tool.poetry]" not in content:
            issues.append(
                Issue(
                    id="pyproject-no-project",
                    analyzer=self.name,
                    severity=Severity.INFO,
                    message="pyproject.toml found but has no [project] or [tool.poetry] section.",
                    file=pyproject_path,
                )
            )

        return issues
