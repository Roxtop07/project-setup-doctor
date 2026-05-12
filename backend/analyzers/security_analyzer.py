from __future__ import annotations

import json
import os
import re

from analyzers.base import BaseAnalyzer
from models.contracts import AutoFix, Issue, ProjectInfo, Severity
from utils.fs import walk_project

SECRET_PATTERNS = [
    (re.compile(r'(?:api[_-]?key|apikey)\s*[=:]\s*["\'][a-zA-Z0-9]{20,}["\']', re.IGNORECASE), "Possible API key"),
    (re.compile(r'(?:password|passwd|pwd)\s*[=:]\s*["\'][^"\']{8,}["\']', re.IGNORECASE), "Possible hardcoded password"),
    (re.compile(r'(?:secret|token)\s*[=:]\s*["\'][a-zA-Z0-9+/=]{20,}["\']', re.IGNORECASE), "Possible secret/token"),
    (re.compile(r'sk-[a-zA-Z0-9]{20,}'), "Possible OpenAI API key"),
    (re.compile(r'ghp_[a-zA-Z0-9]{36,}'), "Possible GitHub personal access token"),
    (re.compile(r'AKIA[0-9A-Z]{16}'), "Possible AWS access key ID"),
]

DANGEROUS_SCRIPT_PATTERNS = [
    re.compile(r"rm\s+-rf\s+/"),
    re.compile(r"curl\s+.*\|\s*sh"),
    re.compile(r"wget\s+.*\|\s*sh"),
]

SCAN_EXTENSIONS = {
    ".ts", ".tsx", ".js", ".jsx", ".mjs", ".cjs",
    ".py", ".pyw",
    ".epl",
    ".rb", ".erb",
    ".java", ".kt", ".kts", ".scala", ".groovy", ".gradle",
    ".go",
    ".rs",
    ".c", ".cpp", ".cc", ".cxx", ".h", ".hpp",
    ".cs",
    ".swift",
    ".php",
    ".r", ".R",
    ".pl", ".pm",
    ".lua",
    ".dart",
    ".ex", ".exs",
    ".hs",
    ".clj", ".cljs",
    ".sh", ".bash", ".zsh",
    ".ps1", ".psm1",
    ".tf", ".hcl",
    ".yml", ".yaml",
    ".toml",
    ".json",
    ".xml",
    ".cfg", ".ini", ".conf",
    ".html", ".htm",
    ".vue", ".svelte",
    ".sql",
}
SCAN_DOTFILES = {".env", ".env.local", ".env.production", ".env.development", ".env.staging"}


class SecurityAnalyzer(BaseAnalyzer):
    name = "security"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        issues: list[Issue] = []
        issues.extend(self._check_gitignore(root_path, project_info))
        issues.extend(self._check_secrets_in_code(root_path))
        issues.extend(self._check_npm_scripts(root_path, project_info))
        return issues

    def _check_gitignore(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        issues: list[Issue] = []
        gitignore_path = os.path.join(root_path, ".gitignore")

        if not os.path.isfile(gitignore_path):
            has_any_project = (
                project_info.has_env_file
                or project_info.has_package_json
                or project_info.has_requirements_txt
                or project_info.has_pyproject_toml
                or project_info.has_go_mod
                or project_info.has_cargo_toml
                or project_info.has_pom_xml
                or project_info.has_build_gradle
                or project_info.has_gemfile
                or project_info.has_composer_json
                or project_info.has_csproj
                or project_info.has_pubspec_yaml
                or project_info.has_mix_exs
                or project_info.has_cmakelists
            )
            if has_any_project:
                entries: list[str] = [".env"]
                if project_info.has_package_json:
                    entries.extend(["node_modules/", "dist/"])
                if project_info.has_requirements_txt or project_info.has_pyproject_toml:
                    entries.extend(["__pycache__/", ".venv/", "*.pyc"])
                if project_info.has_go_mod:
                    entries.append("bin/")
                if project_info.has_cargo_toml:
                    entries.append("target/")
                if project_info.has_pom_xml or project_info.has_build_gradle:
                    entries.extend(["build/", ".gradle/", "target/", "*.class"])
                if project_info.has_gemfile:
                    entries.append("vendor/bundle/")
                if project_info.has_composer_json:
                    entries.append("vendor/")
                if project_info.has_csproj:
                    entries.extend(["bin/", "obj/"])
                if project_info.has_pubspec_yaml:
                    entries.extend([".dart_tool/", "build/"])
                if project_info.has_mix_exs:
                    entries.extend(["_build/", "deps/"])
                if project_info.has_cmakelists:
                    entries.extend(["build/", "*.o", "*.so"])

                issues.append(
                    Issue(
                        id="security-no-gitignore",
                        analyzer=self.name,
                        severity=Severity.WARNING,
                        message="No .gitignore found. Sensitive files may be committed.",
                        fix=AutoFix(
                            id="create-gitignore",
                            description="Create .gitignore",
                            file_create={
                                "path": ".gitignore",
                                "content": "\n".join(sorted(set(entries))) + "\n",
                            },
                        ),
                    )
                )
            return issues

        try:
            with open(gitignore_path) as f:
                content = f.read()
        except OSError:
            return issues

        if ".env" not in content and project_info.has_env_file:
            issues.append(
                Issue(
                    id="security-env-not-ignored",
                    analyzer=self.name,
                    severity=Severity.ERROR,
                    message=".env file exists but is not in .gitignore — secrets may be committed.",
                    file=gitignore_path,
                )
            )

        if project_info.has_package_json and "node_modules" not in content:
            issues.append(
                Issue(
                    id="security-node-modules-not-ignored",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="node_modules/ is not in .gitignore.",
                    file=gitignore_path,
                )
            )

        return issues

    def _check_secrets_in_code(self, root_path: str) -> list[Issue]:
        issues: list[Issue] = []

        for fpath in walk_project(root_path, extensions=SCAN_EXTENSIONS, dotfiles=SCAN_DOTFILES):
            try:
                with open(fpath, errors="ignore") as f:
                    for i, line in enumerate(f, 1):
                        if i > 5000:
                            break
                        for pattern, desc in SECRET_PATTERNS:
                            if pattern.search(line):
                                rel = os.path.relpath(fpath, root_path)
                                issues.append(
                                    Issue(
                                        id=f"security-secret-{rel}-{i}",
                                        analyzer=self.name,
                                        severity=Severity.ERROR,
                                        message=f"{desc} found in {rel}:{i}",
                                        file=fpath,
                                        line=i,
                                    )
                                )
            except OSError:
                continue

        return issues

    def _check_npm_scripts(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        issues: list[Issue] = []
        if not project_info.has_package_json:
            return issues

        pkg_path = os.path.join(root_path, "package.json")
        try:
            with open(pkg_path) as f:
                pkg = json.load(f)
        except (OSError, json.JSONDecodeError):
            return issues

        scripts = pkg.get("scripts", {})
        for name, cmd in scripts.items():
            if not isinstance(cmd, str):
                continue
            for pat in DANGEROUS_SCRIPT_PATTERNS:
                if pat.search(cmd):
                    issues.append(
                        Issue(
                            id=f"security-dangerous-script-{name}",
                            analyzer=self.name,
                            severity=Severity.ERROR,
                            message=f'Potentially dangerous command in npm script "{name}": {cmd}',
                            file=pkg_path,
                        )
                    )

        return issues
