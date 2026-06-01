from __future__ import annotations

import os
from typing import Any, Optional

import pytest

from ai.config import AIConfig
from ai.providers import AIProvider, AIProviderError
from ai.runtime import (
    current_ai_config,
    current_ai_metadata,
    current_existing_issues,
    override_ai_provider,
)
from analyzers.ai_analyzer import AIAnalyzer
from detectors.project_detector import ProjectDetector


class StubProvider:
    def __init__(self, response: dict, calls: list) -> None:
        self.response = response
        self.calls = calls

    async def complete(
        self, system: str, user: str, schema: dict, client: Any = None
    ) -> dict:
        self.calls.append({"system": system, "user": user})
        return self.response


class RaisingProvider:
    async def complete(
        self, system: str, user: str, schema: dict, client: Any = None
    ) -> dict:
        raise AIProviderError("boom")


def _set_ctx(config: Optional[AIConfig], provider: Optional[AIProvider]):
    cfg_token = current_ai_config.set(config)
    prov_token = override_ai_provider.set(provider)
    issues_token = current_existing_issues.set([])
    meta_token = current_ai_metadata.set(None)
    return cfg_token, prov_token, issues_token, meta_token


def _reset_ctx(tokens):
    cfg_token, prov_token, issues_token, meta_token = tokens
    current_ai_metadata.reset(meta_token)
    current_existing_issues.reset(issues_token)
    override_ai_provider.reset(prov_token)
    current_ai_config.reset(cfg_token)


@pytest.mark.asyncio
class TestAIAnalyzer:
    async def test_disabled_returns_empty(self, node_project: str, monkeypatch):
        monkeypatch.delenv("AI_PROVIDER", raising=False)
        monkeypatch.delenv("AI_API_KEY", raising=False)
        info = ProjectDetector(node_project).detect()
        tokens = _set_ctx(None, None)
        try:
            issues = await AIAnalyzer().analyze(node_project, info)
        finally:
            _reset_ctx(tokens)
        assert issues == []
        # No metadata set when AI did not run.
        assert current_ai_metadata.get() is None

    async def test_provider_error_recoverable(self, node_project: str):
        info = ProjectDetector(node_project).detect()
        config = AIConfig(provider="openai", api_key="sk-test")
        tokens = _set_ctx(config, RaisingProvider())
        try:
            issues = await AIAnalyzer().analyze(node_project, info)
            metadata = current_ai_metadata.get()
        finally:
            _reset_ctx(tokens)
        assert issues == []
        assert metadata is not None
        assert metadata.error is not None
        assert metadata.provider == "openai"

    async def test_happy_path_parses_findings(self, node_project: str):
        info = ProjectDetector(node_project).detect()
        config = AIConfig(provider="openai", api_key="sk-test", model="gpt-4o-mini")
        calls: list = []
        provider = StubProvider(
            {
                "findings": [
                    {
                        "severity": "warning",
                        "message": "Missing README badge for build status",
                        "file": "README.md",
                    },
                    {
                        "severity": "info",
                        "message": "Consider pinning Node version in .nvmrc",
                    },
                    # Malformed entry — should be skipped, not crash.
                    {"severity": "warning"},
                ],
                "ai_score": 72.5,
                "ai_summary": "Project is solid but missing a few polish items.",
            },
            calls,
        )
        tokens = _set_ctx(config, provider)
        try:
            issues = await AIAnalyzer().analyze(node_project, info)
            metadata = current_ai_metadata.get()
        finally:
            _reset_ctx(tokens)

        assert len(issues) == 2
        assert all(i.analyzer == "ai" for i in issues)
        assert issues[0].id == "ai-1"
        assert issues[0].severity.value == "warning"
        assert issues[0].file == "README.md"
        assert issues[1].id == "ai-2"
        assert metadata is not None
        assert metadata.score == 72.5
        assert metadata.summary.startswith("Project is solid")
        assert metadata.model == "gpt-4o-mini"
        assert metadata.provider == "openai"
        # Prompt was built and sent.
        assert len(calls) == 1
        assert "## Project summary" in calls[0]["user"]

    async def test_env_fallback(self, node_project: str, monkeypatch):
        monkeypatch.setenv("AI_PROVIDER", "openai")
        monkeypatch.setenv("AI_API_KEY", "env-key")
        info = ProjectDetector(node_project).detect()
        provider = StubProvider(
            {"findings": [], "ai_score": 88, "ai_summary": "all good"},
            calls=[],
        )
        # No request-level config, but env vars present → should still run.
        tokens = _set_ctx(None, provider)
        try:
            issues = await AIAnalyzer().analyze(node_project, info)
            metadata = current_ai_metadata.get()
        finally:
            _reset_ctx(tokens)
        assert issues == []
        assert metadata is not None
        assert metadata.score == 88
