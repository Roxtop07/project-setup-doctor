from __future__ import annotations

import pytest
from detectors.project_detector import ProjectDetector
from models.contracts import ProjectType


class TestProjectDetector:
    def test_detect_node_express(self, node_project: str):
        info = ProjectDetector(node_project).detect()
        assert ProjectType.EXPRESS in info.types
        assert info.has_package_json is True
        assert info.has_env_file is True
        assert info.has_env_example is True
        assert info.has_readme is True
        assert info.has_gitignore is True
        assert "Express" in info.detected_frameworks

    def test_detect_python_fastapi(self, python_project: str):
        info = ProjectDetector(python_project).detect()
        assert ProjectType.FASTAPI in info.types
        assert info.has_requirements_txt is True
        assert info.has_env_file is True
        assert info.has_env_example is False
        assert info.has_gitignore is False
        assert "FastAPI" in info.detected_frameworks

    def test_detect_nextjs(self, nextjs_project: str):
        info = ProjectDetector(nextjs_project).detect()
        assert ProjectType.NEXTJS in info.types
        assert ProjectType.REACT in info.types
        assert info.has_package_json is True
        assert info.has_gitignore is True
        assert "Next.js" in info.detected_frameworks
        assert "React" in info.detected_frameworks

    def test_detect_fullstack(self, fullstack_project: str):
        info = ProjectDetector(fullstack_project).detect()
        assert ProjectType.EXPRESS in info.types
        assert ProjectType.REACT in info.types
        assert ProjectType.FLASK in info.types
        assert ProjectType.DOCKER in info.types
        assert info.has_package_json is True
        assert info.has_requirements_txt is True
        assert info.has_dockerfile is True
        assert info.has_docker_compose is True

    def test_detect_empty(self, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        assert info.types == [ProjectType.UNKNOWN]
        assert info.has_package_json is False
        assert info.has_requirements_txt is False
        assert info.has_dockerfile is False

    def test_detect_broken(self, broken_project: str):
        info = ProjectDetector(broken_project).detect()
        assert ProjectType.NODEJS in info.types
        assert ProjectType.FLASK in info.types
        assert info.has_package_json is True

    def test_project_name(self, node_project: str):
        info = ProjectDetector(node_project).detect()
        assert info.name == "node_project"

    def test_runtime_versions_populated(self, node_project: str):
        info = ProjectDetector(node_project).detect()
        assert "node" in info.runtime_versions
        assert "python" in info.runtime_versions
