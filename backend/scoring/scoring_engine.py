from __future__ import annotations

from typing import Optional

from models.contracts import HealthScore, Issue, ProjectInfo, ScoreBreakdown, Severity

WEIGHTS = {
    "dependency_hygiene": 0.25,
    "docs_quality": 0.15,
    "setup_readiness": 0.25,
    "security": 0.20,
    "environment_completeness": 0.15,
}

PENALTY = {
    Severity.ERROR: 15,
    Severity.WARNING: 8,
    Severity.INFO: 3,
}

ANALYZER_TO_CATEGORY = {
    "dependencies": "dependency_hygiene",
    "readme": "docs_quality",
    "environment": "environment_completeness",
    "security": "security",
    "docker": "setup_readiness",
    "ai": "setup_readiness",
}

AI_BLEND_WEIGHT = 0.3


class ScoringEngine:
    @staticmethod
    def compute(
        project_info: ProjectInfo,
        issues: list[Issue],
        ai_score: Optional[float] = None,
    ) -> HealthScore:
        category_scores: dict[str, float] = {
            "dependency_hygiene": 100.0,
            "docs_quality": 100.0,
            "setup_readiness": 100.0,
            "security": 100.0,
            "environment_completeness": 100.0,
        }

        for issue in issues:
            category = ANALYZER_TO_CATEGORY.get(issue.analyzer, "setup_readiness")
            penalty = PENALTY.get(issue.severity, 5)
            category_scores[category] = max(0, category_scores[category] - penalty)

        category_scores["setup_readiness"] = _adjust_setup_readiness(
            category_scores["setup_readiness"], project_info
        )
        category_scores["docs_quality"] = _adjust_docs_quality(
            category_scores["docs_quality"], project_info
        )

        for key in category_scores:
            category_scores[key] = max(0.0, min(100.0, category_scores[key]))

        total = sum(
            category_scores[k] * WEIGHTS[k] for k in WEIGHTS
        )
        if ai_score is not None:
            clamped_ai = max(0.0, min(100.0, float(ai_score)))
            total = (1 - AI_BLEND_WEIGHT) * total + AI_BLEND_WEIGHT * clamped_ai
        total = max(0.0, min(100.0, total))

        return HealthScore(
            total=round(total, 1),
            breakdown=ScoreBreakdown(**{k: round(v, 1) for k, v in category_scores.items()}),
            grade=_grade(total),
        )


def _adjust_setup_readiness(score: float, info: ProjectInfo) -> float:
    bonuses = 0
    if info.has_gitignore:
        bonuses += 5
    if info.has_env_example:
        bonuses += 5
    if info.has_dockerfile:
        bonuses += 5
    if info.has_docker_compose:
        bonuses += 3
    return min(100, score + bonuses)


def _adjust_docs_quality(score: float, info: ProjectInfo) -> float:
    if info.has_readme:
        score = min(100, score + 10)
    else:
        score = max(0, score - 20)
    return score


def _grade(score: float) -> str:
    if score >= 90:
        return "A"
    if score >= 75:
        return "B"
    if score >= 60:
        return "C"
    if score >= 40:
        return "D"
    return "F"
