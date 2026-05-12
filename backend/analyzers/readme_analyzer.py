from __future__ import annotations

import os
import re

from analyzers.base import BaseAnalyzer
from models.contracts import AutoFix, Issue, ProjectInfo, Severity


class ReadmeAnalyzer(BaseAnalyzer):
    name = "readme"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        issues: list[Issue] = []
        readme_path = self._find_readme(root_path)

        if not readme_path:
            issues.append(
                Issue(
                    id="readme-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="No README found. A README helps other developers understand the project.",
                    fix=AutoFix(
                        id="create-readme",
                        description="Create basic README.md",
                        file_create={
                            "path": "README.md",
                            "content": self._generate_readme(project_info),
                        },
                    ),
                )
            )
            return issues

        try:
            with open(readme_path) as f:
                content = f.read()
        except OSError:
            return issues

        if len(content.strip()) < 50:
            issues.append(
                Issue(
                    id="readme-too-short",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="README is very short (< 50 chars). Consider adding more documentation.",
                    file=readme_path,
                )
            )
            return issues

        content_lower = content.lower()

        install_patterns = [
            r"##?\s*install",
            r"##?\s*getting\s*started",
            r"##?\s*setup",
            r"npm install",
            r"pip install",
            r"yarn add",
        ]
        has_install = any(re.search(p, content_lower) for p in install_patterns)
        if not has_install:
            issues.append(
                Issue(
                    id="readme-no-install",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="README has no install/setup instructions.",
                    file=readme_path,
                )
            )

        run_patterns = [
            r"##?\s*usage",
            r"##?\s*run",
            r"##?\s*quick\s*start",
            r"npm\s+(run\s+)?(start|dev)",
            r"python\s+\w+\.py",
            r"uvicorn\s+",
            r"flask\s+run",
        ]
        has_run = any(re.search(p, content_lower) for p in run_patterns)
        if not has_run:
            issues.append(
                Issue(
                    id="readme-no-run",
                    analyzer=self.name,
                    severity=Severity.INFO,
                    message="README has no run/usage instructions.",
                    file=readme_path,
                )
            )

        env_patterns = [
            r"##?\s*environment",
            r"\.env",
            r"env\s*var",
            r"configuration",
        ]
        has_env_docs = any(re.search(p, content_lower) for p in env_patterns)
        if project_info.has_env_file and not has_env_docs:
            issues.append(
                Issue(
                    id="readme-no-env-docs",
                    analyzer=self.name,
                    severity=Severity.INFO,
                    message="Project uses environment variables but README doesn't document them.",
                    file=readme_path,
                )
            )

        return issues

    def _find_readme(self, root_path: str) -> str | None:
        candidates = ["README.md", "README.rst", "README.txt", "README", "readme.md"]
        for name in candidates:
            p = os.path.join(root_path, name)
            if os.path.isfile(p):
                return p
        return None

    def _generate_readme(self, project_info: ProjectInfo) -> str:
        types = ", ".join(t.value for t in project_info.types if t.value != "unknown")
        lines = [
            f"# {project_info.name}",
            "",
            f"A {types or 'project'} application.",
            "",
            "## Getting Started",
            "",
            "### Prerequisites",
            "",
        ]

        if project_info.has_package_json:
            lines.append("- Node.js")
            lines.append("")
            lines.append("### Installation")
            lines.append("")
            lines.append("```bash")
            lines.append("npm install")
            lines.append("```")
            lines.append("")

        if project_info.has_requirements_txt:
            lines.append("- Python 3")
            lines.append("")
            lines.append("### Installation")
            lines.append("")
            lines.append("```bash")
            lines.append("pip install -r requirements.txt")
            lines.append("```")
            lines.append("")

        lines.extend([
            "## Usage",
            "",
            "```bash",
            "# Add run commands here",
            "```",
            "",
            "## Environment Variables",
            "",
            "Copy `.env.example` to `.env` and fill in the values.",
            "",
        ])

        return "\n".join(lines)
