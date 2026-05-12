from __future__ import annotations

import pytest
from scoring.scoring_engine import ScoringEngine
from detectors.project_detector import ProjectDetector
from models.contracts import Issue, Severity, ProjectInfo, ProjectType


def _make_info(**kwargs) -> ProjectInfo:
    defaults = dict(
        types=[ProjectType.NODEJS],
        root_path="/tmp/test",
        name="test",
        has_package_json=True,
        has_readme=True,
        has_gitignore=True,
    )
    defaults.update(kwargs)
    return ProjectInfo(**defaults)


def _issue(analyzer: str, severity: Severity, msg: str = "test") -> Issue:
    return Issue(id="test", analyzer=analyzer, severity=severity, message=msg)


class TestScoringEngine:
    def test_perfect_score_no_issues(self):
        info = _make_info(
            has_env_example=True,
            has_dockerfile=True,
            has_docker_compose=True,
        )
        score = ScoringEngine.compute(info, [])
        assert score.total >= 90
        assert score.grade == "A"

    def test_errors_reduce_score(self):
        info = _make_info()
        issues = [
            _issue("dependencies", Severity.ERROR),
            _issue("dependencies", Severity.ERROR),
            _issue("security", Severity.ERROR),
        ]
        score = ScoringEngine.compute(info, issues)
        assert score.total < 90
        assert score.breakdown.dependency_hygiene < 100
        assert score.breakdown.security < 100

    def test_warnings_less_impact_than_errors(self):
        info = _make_info()
        errors = [_issue("dependencies", Severity.ERROR)]
        warnings = [_issue("dependencies", Severity.WARNING)]
        score_err = ScoringEngine.compute(info, errors)
        score_warn = ScoringEngine.compute(info, warnings)
        assert score_warn.total > score_err.total

    def test_info_least_impact(self):
        info = _make_info()
        infos = [_issue("readme", Severity.INFO)]
        score = ScoringEngine.compute(info, infos)
        assert score.total >= 80

    def test_grade_boundaries(self):
        info = _make_info()
        score_a = ScoringEngine.compute(info, [])
        assert score_a.grade in ("A", "B")

        many_errors = []
        for analyzer in ["dependencies", "security", "readme", "environment", "docker"]:
            many_errors.extend([_issue(analyzer, Severity.ERROR) for _ in range(8)])
        score_low = ScoringEngine.compute(info, many_errors)
        assert score_low.grade in ("C", "D", "F")

    def test_no_readme_penalizes_docs(self):
        info = _make_info(has_readme=False)
        score = ScoringEngine.compute(info, [])
        assert score.breakdown.docs_quality < 100

    def test_env_example_boosts_setup(self):
        info_without = _make_info(has_env_example=False)
        info_with = _make_info(has_env_example=True)
        score_without = ScoringEngine.compute(info_without, [])
        score_with = ScoringEngine.compute(info_with, [])
        assert score_with.breakdown.setup_readiness >= score_without.breakdown.setup_readiness

    def test_score_clamped_0_100(self):
        info = _make_info()
        many_issues = [_issue("security", Severity.ERROR) for _ in range(50)]
        score = ScoringEngine.compute(info, many_issues)
        assert 0 <= score.total <= 100
        assert 0 <= score.breakdown.security <= 100

    def test_real_node_project(self, node_project: str):
        info = ProjectDetector(node_project).detect()
        score = ScoringEngine.compute(info, [])
        assert 0 <= score.total <= 100
        assert score.grade in ("A", "B", "C", "D", "F")

    def test_real_empty_project(self, empty_project: str):
        info = ProjectDetector(empty_project).detect()
        score = ScoringEngine.compute(info, [])
        assert 0 <= score.total <= 100
