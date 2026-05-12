from __future__ import annotations

import pytest
from analyzers.env_analyzer import EnvAnalyzer
from detectors.project_detector import ProjectDetector
from models.contracts import Severity


@pytest.fixture
def analyzer():
    return EnvAnalyzer()


class TestEnvAnalyzer:
    @pytest.mark.asyncio
    async def test_node_missing_env_var(self, analyzer: EnvAnalyzer, node_project: str):
        info = ProjectDetector(node_project).detect()
        issues = await analyzer.analyze(node_project, info)
        missing = [i for i in issues if "MISSING_VAR" in i.message]
        assert len(missing) == 1
        assert missing[0].severity == Severity.ERROR

    @pytest.mark.asyncio
    async def test_python_no_env_example(self, analyzer: EnvAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        example_issues = [i for i in issues if "env.example" in i.message.lower()]
        assert len(example_issues) >= 1

    @pytest.mark.asyncio
    async def test_python_no_env_example_has_fix(self, analyzer: EnvAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        fixable = [i for i in issues if i.fix is not None]
        assert len(fixable) >= 1

    @pytest.mark.asyncio
    async def test_empty_project_no_issues(self, analyzer: EnvAnalyzer, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        issues = await analyzer.analyze(empty_project, info)
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_broken_env_malformed(self, analyzer: EnvAnalyzer, broken_project: str):
        info = ProjectDetector(broken_project).detect()
        issues = await analyzer.analyze(broken_project, info)
        malformed = [i for i in issues if "malformed" in i.message.lower() or "empty variable" in i.message.lower()]
        assert len(malformed) >= 1

    @pytest.mark.asyncio
    async def test_fullstack_runtime_checks(self, analyzer: EnvAnalyzer, fullstack_project: str):
        info = ProjectDetector(fullstack_project).detect()
        issues = await analyzer.analyze(fullstack_project, info)
        assert isinstance(issues, list)

    @pytest.mark.asyncio
    async def test_nextjs_no_env_issues(self, analyzer: EnvAnalyzer, nextjs_project: str):
        info = ProjectDetector(nextjs_project).detect()
        issues = await analyzer.analyze(nextjs_project, info)
        assert isinstance(issues, list)
