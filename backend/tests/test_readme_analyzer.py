from __future__ import annotations

import pytest
from analyzers.readme_analyzer import ReadmeAnalyzer
from detectors.project_detector import ProjectDetector
from models.contracts import Severity


@pytest.fixture
def analyzer():
    return ReadmeAnalyzer()


class TestReadmeAnalyzer:
    @pytest.mark.asyncio
    async def test_node_readme_no_env_docs(self, analyzer: ReadmeAnalyzer, node_project: str):
        info = ProjectDetector(node_project).detect()
        issues = await analyzer.analyze(node_project, info)
        env_issues = [i for i in issues if "environment" in i.message.lower()]
        assert len(env_issues) >= 1

    @pytest.mark.asyncio
    async def test_python_readme_too_short(self, analyzer: ReadmeAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        short = [i for i in issues if "short" in i.message.lower()]
        assert len(short) == 1

    @pytest.mark.asyncio
    async def test_nextjs_readme_good(self, analyzer: ReadmeAnalyzer, nextjs_project: str):
        info = ProjectDetector(nextjs_project).detect()
        issues = await analyzer.analyze(nextjs_project, info)
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_empty_no_readme(self, analyzer: ReadmeAnalyzer, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        issues = await analyzer.analyze(empty_project, info)
        missing = [i for i in issues if "no readme" in i.message.lower()]
        assert len(missing) == 1
        assert missing[0].fix is not None
        assert missing[0].fix.file_create is not None

    @pytest.mark.asyncio
    async def test_broken_no_readme(self, analyzer: ReadmeAnalyzer, broken_project: str):
        info = ProjectDetector(broken_project).detect()
        issues = await analyzer.analyze(broken_project, info)
        missing = [i for i in issues if "no readme" in i.message.lower()]
        assert len(missing) == 1

    @pytest.mark.asyncio
    async def test_fullstack_readme_complete(self, analyzer: ReadmeAnalyzer, fullstack_project: str):
        info = ProjectDetector(fullstack_project).detect()
        issues = await analyzer.analyze(fullstack_project, info)
        assert len(issues) == 0
