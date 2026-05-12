from __future__ import annotations

import os
import pytest
from analyzers.epl_analyzer import EplAnalyzer
from detectors.project_detector import ProjectDetector


class TestEplAnalyzer:
    @pytest.fixture
    def analyzer(self) -> EplAnalyzer:
        return EplAnalyzer()

    @pytest.mark.asyncio
    async def test_epl_project_detected(self, epl_project: str):
        info = ProjectDetector(epl_project).detect()
        analyzer = EplAnalyzer()
        issues = await analyzer.analyze(epl_project, info)
        ids = [i.id for i in issues]
        assert "epl-missing-eplang" not in ids
        assert "epl-gitignore-incomplete" in ids

    @pytest.mark.asyncio
    async def test_epl_gitignore_missing_entries(self, epl_project: str):
        info = ProjectDetector(epl_project).detect()
        analyzer = EplAnalyzer()
        issues = await analyzer.analyze(epl_project, info)
        gitignore_issue = next(i for i in issues if i.id == "epl-gitignore-incomplete")
        assert "__eplcache__" in gitignore_issue.message
        assert "*.eplc" in gitignore_issue.message
        assert "deploy/" in gitignore_issue.message

    @pytest.mark.asyncio
    async def test_empty_project_skipped(self, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        analyzer = EplAnalyzer()
        issues = await analyzer.analyze(empty_project, info)
        assert issues == []

    @pytest.mark.asyncio
    async def test_epl_missing_eplang(self, tmp_path):
        (tmp_path / "hello.epl").write_text('show "hi"')
        (tmp_path / ".gitignore").write_text("__eplcache__/\n*.eplc\ndeploy/\n")
        info = ProjectDetector(str(tmp_path)).detect()
        analyzer = EplAnalyzer()
        issues = await analyzer.analyze(str(tmp_path), info)
        ids = [i.id for i in issues]
        assert "epl-missing-eplang" in ids

    @pytest.mark.asyncio
    async def test_epl_no_main_entry_point(self, tmp_path):
        (tmp_path / "app.epl").write_text('show "no main"')
        (tmp_path / "requirements.txt").write_text("eplang\n")
        info = ProjectDetector(str(tmp_path)).detect()
        analyzer = EplAnalyzer()
        issues = await analyzer.analyze(str(tmp_path), info)
        ids = [i.id for i in issues]
        assert "epl-no-main" in ids
