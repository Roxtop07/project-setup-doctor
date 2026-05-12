from __future__ import annotations

import pytest
from analyzers.docker_analyzer import DockerAnalyzer
from detectors.project_detector import ProjectDetector
from models.contracts import Severity


@pytest.fixture
def analyzer():
    return DockerAnalyzer()


class TestDockerAnalyzer:
    @pytest.mark.asyncio
    async def test_node_no_dockerfile_suggests(self, analyzer: DockerAnalyzer, node_project: str):
        info = ProjectDetector(node_project).detect()
        issues = await analyzer.analyze(node_project, info)
        no_docker = [i for i in issues if "no dockerfile" in i.message.lower()]
        assert len(no_docker) == 1
        assert no_docker[0].severity == Severity.INFO
        assert no_docker[0].fix is not None
        assert "FROM node" in no_docker[0].fix.file_create["content"]

    @pytest.mark.asyncio
    async def test_python_no_dockerfile_suggests_python(self, analyzer: DockerAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        no_docker = [i for i in issues if "no dockerfile" in i.message.lower()]
        assert len(no_docker) == 1
        assert "FROM python" in no_docker[0].fix.file_create["content"]

    @pytest.mark.asyncio
    async def test_fullstack_latest_tag_warning(self, analyzer: DockerAnalyzer, fullstack_project: str):
        info = ProjectDetector(fullstack_project).detect()
        issues = await analyzer.analyze(fullstack_project, info)
        latest = [i for i in issues if "latest" in i.message.lower()]
        assert len(latest) == 1
        assert latest[0].severity == Severity.WARNING

    @pytest.mark.asyncio
    async def test_fullstack_no_user_directive(self, analyzer: DockerAnalyzer, fullstack_project: str):
        info = ProjectDetector(fullstack_project).detect()
        issues = await analyzer.analyze(fullstack_project, info)
        no_user = [i for i in issues if "non-root USER" in i.message]
        assert len(no_user) == 1

    @pytest.mark.asyncio
    async def test_fullstack_no_dockerignore(self, analyzer: DockerAnalyzer, fullstack_project: str):
        info = ProjectDetector(fullstack_project).detect()
        issues = await analyzer.analyze(fullstack_project, info)
        no_di = [i for i in issues if "dockerignore" in i.message.lower()]
        assert len(no_di) == 1
        assert no_di[0].fix is not None

    @pytest.mark.asyncio
    async def test_empty_no_issues(self, analyzer: DockerAnalyzer, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        issues = await analyzer.analyze(empty_project, info)
        assert len(issues) == 0
