from __future__ import annotations

import os
import shutil

from analyzers.base import BaseAnalyzer
from models.contracts import Issue, ProjectInfo, ProjectType, Severity


class JvmAnalyzer(BaseAnalyzer):
    name = "jvm"

    async def analyze(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        jvm_types = {ProjectType.JAVA, ProjectType.KOTLIN, ProjectType.SCALA}
        if not jvm_types & set(project_info.types):
            return []

        issues: list[Issue] = []
        issues.extend(self._check_runtime(project_info))
        issues.extend(self._check_wrapper(root_path, project_info))
        issues.extend(self._check_gitignore(root_path, project_info))
        return issues

    def _check_runtime(self, project_info: ProjectInfo) -> list[Issue]:
        if project_info.runtime_versions.get("java") is not None:
            return []
        if not shutil.which("java"):
            return [
                Issue(
                    id="jvm-runtime-missing",
                    analyzer=self.name,
                    severity=Severity.WARNING,
                    message="Java runtime not found on PATH.",
                )
            ]
        return []

    def _check_wrapper(
        self, root_path: str, project_info: ProjectInfo
    ) -> list[Issue]:
        if project_info.has_build_gradle:
            if not os.path.isfile(os.path.join(root_path, "gradlew")):
                return [
                    Issue(
                        id="jvm-no-gradle-wrapper",
                        analyzer=self.name,
                        severity=Severity.INFO,
                        message="Gradle project without gradlew wrapper. Consider adding it for reproducible builds.",
                    )
                ]
        if project_info.has_pom_xml:
            if not os.path.isfile(os.path.join(root_path, "mvnw")):
                return [
                    Issue(
                        id="jvm-no-maven-wrapper",
                        analyzer=self.name,
                        severity=Severity.INFO,
                        message="Maven project without mvnw wrapper. Consider adding it for reproducible builds.",
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
        for entry in ["build/", ".gradle", "target/", "*.class"]:
            if entry not in content:
                missing.append(entry)

        if not missing:
            return []

        return [
            Issue(
                id="jvm-gitignore-incomplete",
                analyzer=self.name,
                severity=Severity.WARNING,
                message=f"JVM build artifacts not in .gitignore: {', '.join(missing)}",
                file=gitignore_path,
            )
        ]
