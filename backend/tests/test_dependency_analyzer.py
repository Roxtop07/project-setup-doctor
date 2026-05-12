from __future__ import annotations

import pytest
from analyzers.dependency_analyzer import DependencyAnalyzer
from detectors.project_detector import ProjectDetector
from models.contracts import Severity


@pytest.fixture
def analyzer():
    return DependencyAnalyzer()


class TestDependencyAnalyzer:
    @pytest.mark.asyncio
    async def test_node_no_lockfile(self, analyzer: DependencyAnalyzer, node_project: str):
        info = ProjectDetector(node_project).detect()
        issues = await analyzer.analyze(node_project, info)
        lockfile_issues = [i for i in issues if "lockfile" in i.message.lower()]
        assert len(lockfile_issues) == 1
        assert lockfile_issues[0].severity == Severity.WARNING

    @pytest.mark.asyncio
    async def test_node_no_node_modules(self, analyzer: DependencyAnalyzer, node_project: str):
        info = ProjectDetector(node_project).detect()
        issues = await analyzer.analyze(node_project, info)
        missing = [i for i in issues if "node_modules" in i.message]
        assert len(missing) == 1
        assert missing[0].severity == Severity.ERROR
        assert missing[0].fix is not None
        assert missing[0].fix.command == "npm install"

    @pytest.mark.asyncio
    async def test_python_duplicate_package(self, analyzer: DependencyAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        dupes = [i for i in issues if "duplicate" in i.message.lower()]
        assert len(dupes) >= 1

    @pytest.mark.asyncio
    async def test_python_unpinned_package(self, analyzer: DependencyAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        unpinned = [i for i in issues if "no version constraint" in i.message.lower()]
        assert len(unpinned) >= 1

    @pytest.mark.asyncio
    async def test_nextjs_duplicate_overlap(self, analyzer: DependencyAnalyzer, nextjs_project: str):
        info = ProjectDetector(nextjs_project).detect()
        issues = await analyzer.analyze(nextjs_project, info)
        overlap = [i for i in issues if "both dependencies and devDependencies" in i.message]
        assert len(overlap) >= 1

    @pytest.mark.asyncio
    async def test_nextjs_unpinned_star(self, analyzer: DependencyAnalyzer, nextjs_project: str):
        info = ProjectDetector(nextjs_project).detect()
        issues = await analyzer.analyze(nextjs_project, info)
        unpinned = [i for i in issues if 'unpinned version' in i.message.lower()]
        assert len(unpinned) >= 1

    @pytest.mark.asyncio
    async def test_empty_project_no_issues(self, analyzer: DependencyAnalyzer, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        issues = await analyzer.analyze(empty_project, info)
        assert len(issues) == 0

    @pytest.mark.asyncio
    async def test_nextjs_has_lockfile_no_warning(self, analyzer: DependencyAnalyzer, nextjs_project: str):
        info = ProjectDetector(nextjs_project).detect()
        issues = await analyzer.analyze(nextjs_project, info)
        lockfile_issues = [i for i in issues if "lockfile" in i.message.lower()]
        assert len(lockfile_issues) == 0

    @pytest.mark.asyncio
    async def test_python_no_venv(self, analyzer: DependencyAnalyzer, python_project: str):
        info = ProjectDetector(python_project).detect()
        issues = await analyzer.analyze(python_project, info)
        venv = [i for i in issues if "virtual environment" in i.message.lower()]
        assert len(venv) == 1
        assert venv[0].fix is not None
