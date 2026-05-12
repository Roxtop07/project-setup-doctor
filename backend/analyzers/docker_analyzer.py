from __future__ import annotations

import os
import re

from analyzers.base import BaseAnalyzer
from models.contracts import AutoFix, Issue, ProjectInfo, Severity


class DockerAnalyzer(BaseAnalyzer):
    name = "docker"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        issues: list[Issue] = []

        if not project_info.has_dockerfile:
            if project_info.has_package_json or project_info.has_requirements_txt:
                issues.append(
                    Issue(
                        id="docker-no-dockerfile",
                        analyzer=self.name,
                        severity=Severity.INFO,
                        message="No Dockerfile found. Consider containerizing the application.",
                        fix=AutoFix(
                            id="create-dockerfile",
                            description="Generate basic Dockerfile",
                            file_create={
                                "path": "Dockerfile",
                                "content": self._generate_dockerfile(project_info),
                            },
                        ),
                    )
                )
            return issues

        dockerfile_path = os.path.join(root_path, "Dockerfile")
        try:
            with open(dockerfile_path) as f:
                content = f.read()
        except OSError:
            return issues

        if ":latest" in content:
            issues.append(
                Issue(
                    id="docker-latest-tag",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Dockerfile uses :latest tag. Pin to a specific version for reproducible builds.",
                    file=dockerfile_path,
                )
            )

        if not re.search(r"^USER\s+", content, re.MULTILINE):
            issues.append(
                Issue(
                    id="docker-no-user",
                    analyzer=self.name,
                    severity=Severity.INFO,
                    message="Dockerfile does not set a non-root USER. Consider adding one for security.",
                    file=dockerfile_path,
                )
            )

        dockerignore_path = os.path.join(root_path, ".dockerignore")
        if not os.path.isfile(dockerignore_path):
            issues.append(
                Issue(
                    id="docker-no-dockerignore",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="No .dockerignore found. Build context may include unnecessary files.",
                    fix=AutoFix(
                        id="create-dockerignore",
                        description="Create .dockerignore",
                        file_create={
                            "path": ".dockerignore",
                            "content": "node_modules\n.git\n.env\n__pycache__\n.venv\nvenv\ndist\nbuild\n*.pyc\n.DS_Store\n",
                        },
                    ),
                )
            )

        return issues

    def _generate_dockerfile(self, project_info: ProjectInfo) -> str:
        if project_info.has_package_json:
            return (
                "FROM node:20-alpine\n"
                "WORKDIR /app\n"
                "COPY package*.json ./\n"
                "RUN npm ci --only=production\n"
                "COPY . .\n"
                "EXPOSE 3000\n"
                'CMD ["node", "index.js"]\n'
            )

        return (
            "FROM python:3.12-slim\n"
            "WORKDIR /app\n"
            "COPY requirements.txt .\n"
            "RUN pip install --no-cache-dir -r requirements.txt\n"
            "COPY . .\n"
            "EXPOSE 8000\n"
            'CMD ["python", "main.py"]\n'
        )
