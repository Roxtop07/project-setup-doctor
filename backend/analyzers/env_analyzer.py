from __future__ import annotations

import os
import re
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import AutoFix, Issue, ProjectInfo, Severity
from utils.fs import safe_read, walk_project

ENV_REF_PATTERNS = [
    re.compile(r"process\.env\.(\w+)"),
    re.compile(r'os\.environ\[[\'"]([\w]+)[\'"]\]'),
    re.compile(r'os\.environ\.get\([\'"]([\w]+)[\'"]'),
    re.compile(r'os\.getenv\([\'"]([\w]+)[\'"]'),
]

COMMON_SKIP_VARS = frozenset({"NODE_ENV", "PATH", "HOME", "USER", "PWD", "SHELL", "TERM", "LANG"})


class EnvAnalyzer(BaseAnalyzer):
    name = "environment"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        issues: list[Issue] = []

        env_path = os.path.join(root_path, ".env")
        env_example_path = os.path.join(root_path, ".env.example")
        has_env = os.path.isfile(env_path)
        has_example = os.path.isfile(env_example_path)

        if not has_env and not has_example:
            referenced = self._find_env_references(root_path)
            if referenced:
                content = "\n".join(f"{v}=" for v in sorted(referenced)) + "\n"
                issues.append(
                    Issue(
                        id="env-missing",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message="No .env or .env.example found, but code references environment variables.",
                        fix=AutoFix(
                            id="create-env-example",
                            description="Create .env.example with detected variables",
                            file_create={
                                "path": ".env.example",
                                "content": content,
                            },
                        ),
                    )
                )
            return issues

        if has_env and not has_example:
            env_vars = self._parse_env_file(env_path)
            content = "\n".join(f"{v}=" for v in env_vars) + "\n"
            issues.append(
                Issue(
                    id="env-example-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Found .env but no .env.example — other developers won't know which variables are needed.",
                    fix=AutoFix(
                        id="create-env-example",
                        description="Generate .env.example from .env",
                        file_create={
                            "path": ".env.example",
                            "content": content,
                        },
                    ),
                )
            )

        if has_example and has_env:
            example_vars = set(self._parse_env_file(env_example_path))
            env_vars = set(self._parse_env_file(env_path))
            missing = example_vars - env_vars
            for var in sorted(missing):
                issues.append(
                    Issue(
                        id=f"env-var-missing-{var.lower()}",
                        analyzer=self.name,
                        severity=Severity.ERROR,
                        message=f"{var} is in .env.example but missing from .env",
                        file=env_path,
                    )
                )

        if has_env:
            issues.extend(self._check_malformed(env_path))

        issues.extend(self._check_runtime_versions(project_info))

        return issues

    def _parse_env_file(self, path: str) -> list[str]:
        variables: list[str] = []
        try:
            with open(path) as f:
                for line in f:
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    key = line.split("=", 1)[0].strip()
                    if key:
                        variables.append(key)
        except OSError:
            pass
        return variables

    def _check_malformed(self, env_path: str) -> list[Issue]:
        issues: list[Issue] = []
        try:
            with open(env_path) as f:
                for i, line in enumerate(f, 1):
                    line = line.strip()
                    if not line or line.startswith("#"):
                        continue
                    if "=" not in line:
                        issues.append(
                            Issue(
                                id=f"env-malformed-{i}",
                                analyzer=self.name,
                                severity=Severity.WARNING,
                                message=f"Malformed line {i}: missing '=' separator",
                                file=env_path,
                                line=i,
                            )
                        )
                    elif line.startswith("="):
                        issues.append(
                            Issue(
                                id=f"env-no-key-{i}",
                                analyzer=self.name,
                                severity=Severity.WARNING,
                                message=f"Line {i}: empty variable name",
                                file=env_path,
                                line=i,
                            )
                        )
        except OSError:
            pass
        return issues

    def _find_env_references(self, root_path: str) -> set[str]:
        found: set[str] = set()
        extensions = {".ts", ".tsx", ".js", ".jsx", ".py"}

        for fpath in walk_project(root_path, extensions=extensions):
            content = safe_read(fpath)
            if content is None:
                continue
            for pat in ENV_REF_PATTERNS:
                found.update(pat.findall(content))

        return found - COMMON_SKIP_VARS

    def _check_runtime_versions(self, project_info: ProjectInfo) -> list[Issue]:
        issues: list[Issue] = []

        if project_info.has_package_json:
            if not shutil.which("node"):
                issues.append(
                    Issue(
                        id="runtime-node-missing",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message="Node.js not found on PATH — required for this project.",
                    )
                )
            if not shutil.which("npm"):
                issues.append(
                    Issue(
                        id="runtime-npm-missing",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message="npm not found on PATH.",
                    )
                )

        if project_info.has_requirements_txt or project_info.has_pyproject_toml:
            if not (shutil.which("python3") or shutil.which("python")):
                issues.append(
                    Issue(
                        id="runtime-python-missing",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message="Python not found on PATH — required for this project.",
                    )
                )
            if not (shutil.which("pip3") or shutil.which("pip")):
                issues.append(
                    Issue(
                        id="runtime-pip-missing",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message="pip not found on PATH.",
                    )
                )

        if project_info.has_dockerfile or project_info.has_docker_compose:
            if not shutil.which("docker"):
                issues.append(
                    Issue(
                        id="runtime-docker-missing",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message="Docker not found on PATH — Dockerfile present but Docker not installed.",
                    )
                )

        return issues
