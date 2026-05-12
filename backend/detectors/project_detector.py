from __future__ import annotations

import json
import os
import shutil
import subprocess

from models.contracts import ProjectInfo, ProjectType


class ProjectDetector:
    def __init__(self, root_path: str):
        self.root = root_path

    def detect(self) -> ProjectInfo:
        name = os.path.basename(os.path.abspath(self.root))
        types: list[ProjectType] = []
        frameworks: list[str] = []

        has_pkg = os.path.isfile(self._p("package.json"))
        has_req = os.path.isfile(self._p("requirements.txt"))
        has_pyproject = os.path.isfile(self._p("pyproject.toml"))
        has_dockerfile = os.path.isfile(self._p("Dockerfile"))
        has_compose = any(
            os.path.isfile(self._p(f))
            for f in ["docker-compose.yml", "docker-compose.yaml", "compose.yml", "compose.yaml"]
        )
        has_env = os.path.isfile(self._p(".env"))
        has_env_example = os.path.isfile(self._p(".env.example"))
        has_readme = any(
            os.path.isfile(self._p(f))
            for f in ["README.md", "README.rst", "README.txt", "README"]
        )
        has_gitignore = os.path.isfile(self._p(".gitignore"))

        if has_pkg:
            pkg_types, pkg_frameworks = self._detect_node_project()
            types.extend(pkg_types)
            frameworks.extend(pkg_frameworks)

        if has_req or has_pyproject:
            py_types, py_frameworks = self._detect_python_project()
            types.extend(py_types)
            frameworks.extend(py_frameworks)

        if has_dockerfile:
            types.append(ProjectType.DOCKER)

        if not types:
            types.append(ProjectType.UNKNOWN)

        versions = self._detect_runtime_versions()

        return ProjectInfo(
            types=list(dict.fromkeys(types)),
            root_path=self.root,
            name=name,
            has_package_json=has_pkg,
            has_requirements_txt=has_req,
            has_pyproject_toml=has_pyproject,
            has_dockerfile=has_dockerfile,
            has_docker_compose=has_compose,
            has_env_file=has_env,
            has_env_example=has_env_example,
            has_readme=has_readme,
            has_gitignore=has_gitignore,
            detected_frameworks=list(dict.fromkeys(frameworks)),
            runtime_versions=versions,
        )

    def _detect_node_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = []
        frameworks: list[str] = []

        try:
            pkg_path = self._p("package.json")
            if os.path.getsize(pkg_path) > 5_000_000:
                types.append(ProjectType.NODEJS)
                return types, frameworks
            with open(pkg_path) as f:
                pkg = json.load(f)
        except (OSError, json.JSONDecodeError):
            types.append(ProjectType.NODEJS)
            return types, frameworks

        all_deps = {
            **pkg.get("dependencies", {}),
            **pkg.get("devDependencies", {}),
        }

        if "next" in all_deps:
            types.append(ProjectType.NEXTJS)
            frameworks.append("Next.js")
        if "react" in all_deps:
            types.append(ProjectType.REACT)
            frameworks.append("React")
        if "express" in all_deps:
            types.append(ProjectType.EXPRESS)
            frameworks.append("Express")
        if "vue" in all_deps:
            frameworks.append("Vue.js")
        if "svelte" in all_deps or "svelte-kit" in all_deps:
            frameworks.append("Svelte")
        if "@angular/core" in all_deps:
            frameworks.append("Angular")
        if "vite" in all_deps:
            frameworks.append("Vite")

        if not types:
            types.append(ProjectType.NODEJS)

        return types, frameworks

    def _detect_python_project(self) -> tuple[list[ProjectType], list[str]]:
        types: list[ProjectType] = []
        frameworks: list[str] = []

        deps_text = ""
        for fname in ["requirements.txt", "pyproject.toml", "setup.py", "Pipfile"]:
            p = self._p(fname)
            if os.path.isfile(p):
                try:
                    with open(p) as f:
                        deps_text += f.read().lower() + "\n"
                except OSError:
                    pass

        if "fastapi" in deps_text:
            types.append(ProjectType.FASTAPI)
            frameworks.append("FastAPI")
        if "flask" in deps_text:
            types.append(ProjectType.FLASK)
            frameworks.append("Flask")
        if "django" in deps_text:
            types.append(ProjectType.DJANGO)
            frameworks.append("Django")

        if not types:
            types.append(ProjectType.PYTHON)

        if "celery" in deps_text:
            frameworks.append("Celery")
        if "sqlalchemy" in deps_text:
            frameworks.append("SQLAlchemy")
        if "pytest" in deps_text:
            frameworks.append("pytest")

        return types, frameworks

    def _detect_runtime_versions(self) -> dict[str, str | None]:
        versions: dict[str, str | None] = {}

        for cmd, key in [
            (["node", "--version"], "node"),
            (["npm", "--version"], "npm"),
            (["python3", "--version"], "python"),
            (["pip3", "--version"], "pip"),
            (["docker", "--version"], "docker"),
        ]:
            if not shutil.which(cmd[0]):
                versions[key] = None
                continue
            try:
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                versions[key] = result.stdout.strip().split()[-1] if result.returncode == 0 else None
            except (subprocess.TimeoutExpired, OSError):
                versions[key] = None

        return versions

    def _p(self, *parts: str) -> str:
        return os.path.join(self.root, *parts)
