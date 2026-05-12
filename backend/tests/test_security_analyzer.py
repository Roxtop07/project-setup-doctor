from __future__ import annotations

import pytest
from analyzers.security_analyzer import SecurityAnalyzer
from detectors.project_detector import ProjectDetector
from models.contracts import Severity


@pytest.fixture
def analyzer():
    return SecurityAnalyzer()


class TestSecurityAnalyzer:
    @pytest.mark.asyncio
    async def test_python_no_gitignore(self, analyzer: SecurityAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        gi = [i for i in issues if "gitignore" in i.message.lower()]
        assert len(gi) >= 1
        assert gi[0].fix is not None

    @pytest.mark.asyncio
    async def test_node_gitignore_ok(self, analyzer: SecurityAnalyzer, node_project: str):
        info = ProjectDetector(node_project).detect()
        issues = await analyzer.analyze(node_project, info)
        gi = [i for i in issues if "no .gitignore" in i.message.lower()]
        assert len(gi) == 0

    @pytest.mark.asyncio
    async def test_fullstack_potential_secret(self, analyzer: SecurityAnalyzer, fullstack_project: str):
        info = ProjectDetector(fullstack_project).detect()
        issues = await analyzer.analyze(fullstack_project, info)
        secrets = [i for i in issues if "possible" in i.message.lower() and i.severity == Severity.ERROR]
        assert len(secrets) >= 1

    @pytest.mark.asyncio
    async def test_empty_no_issues(self, analyzer: SecurityAnalyzer, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        issues = await analyzer.analyze(empty_project, info)
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_broken_no_gitignore(self, analyzer: SecurityAnalyzer, broken_project: str):
        info = ProjectDetector(broken_project).detect()
        issues = await analyzer.analyze(broken_project, info)
        gi = [i for i in issues if "gitignore" in i.message.lower()]
        assert len(gi) >= 1
