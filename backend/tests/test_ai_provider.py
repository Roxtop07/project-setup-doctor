from __future__ import annotations

import json

import httpx
import pytest

from ai.config import AIConfig
from ai.providers import (
    AIProviderError,
    AnthropicProvider,
    GeminiProvider,
    OpenAICompatibleProvider,
    OpenAIProvider,
    _extract_first_json_object,
    build_provider,
)


SCHEMA = {"type": "object"}


def _mock_client(handler) -> httpx.AsyncClient:
    return httpx.AsyncClient(transport=httpx.MockTransport(handler))


class TestExtractJSON:
    def test_plain_json(self):
        assert _extract_first_json_object('{"a": 1}') == {"a": 1}

    def test_fenced_json(self):
        assert _extract_first_json_object('```json\n{"a": 1}\n```') == {"a": 1}

    def test_json_inside_prose(self):
        text = 'Here you go: {"a": 1, "b": 2} hope that helps'
        assert _extract_first_json_object(text) == {"a": 1, "b": 2}

    def test_no_json_raises(self):
        with pytest.raises(AIProviderError):
            _extract_first_json_object("no json here")


@pytest.mark.asyncio
class TestOpenAIProvider:
    async def test_request_shape_and_parse(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["auth"] = request.headers.get("authorization")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"findings": [], "ai_score": 80, "ai_summary": "ok"}
                                )
                            }
                        }
                    ]
                },
            )

        provider = OpenAIProvider(
            AIConfig(
                provider="openai", api_key="sk-test", model="gpt-4o-mini",
            )
        )
        async with _mock_client(handler) as client:
            result = await provider.complete("sys", "usr", SCHEMA, client=client)

        assert result["ai_score"] == 80
        assert captured["auth"] == "Bearer sk-test"
        assert captured["body"]["model"] == "gpt-4o-mini"
        assert captured["body"]["response_format"] == {"type": "json_object"}
        assert "chat/completions" in captured["url"]

    async def test_http_error_raises(self):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(401, text="unauthorized")

        provider = OpenAIProvider(AIConfig(provider="openai", api_key="bad"))
        async with _mock_client(handler) as client:
            with pytest.raises(AIProviderError):
                await provider.complete("sys", "usr", SCHEMA, client=client)


@pytest.mark.asyncio
class TestAnthropicProvider:
    async def test_request_shape_and_parse(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["api_key"] = request.headers.get("x-api-key")
            captured["version"] = request.headers.get("anthropic-version")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "content": [
                        {
                            "type": "text",
                            "text": json.dumps(
                                {"findings": [], "ai_score": 70, "ai_summary": "fine"}
                            ),
                        }
                    ]
                },
            )

        provider = AnthropicProvider(
            AIConfig(provider="anthropic", api_key="ak-test", model="claude-haiku-4-5")
        )
        async with _mock_client(handler) as client:
            result = await provider.complete("sys", "usr", SCHEMA, client=client)

        assert result["ai_summary"] == "fine"
        assert captured["api_key"] == "ak-test"
        assert captured["version"] == "2023-06-01"
        assert captured["body"]["model"] == "claude-haiku-4-5"
        assert captured["body"]["system"] == "sys"
        assert captured["url"].endswith("/v1/messages")


@pytest.mark.asyncio
class TestGeminiProvider:
    async def test_request_shape_and_parse(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["url"] = str(request.url)
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "candidates": [
                        {
                            "content": {
                                "parts": [
                                    {
                                        "text": json.dumps(
                                            {
                                                "findings": [],
                                                "ai_score": 65,
                                                "ai_summary": "ok",
                                            }
                                        )
                                    }
                                ]
                            }
                        }
                    ]
                },
            )

        provider = GeminiProvider(
            AIConfig(provider="gemini", api_key="gk-test", model="gemini-2.0-flash")
        )
        async with _mock_client(handler) as client:
            result = await provider.complete("sys", "usr", SCHEMA, client=client)

        assert result["ai_score"] == 65
        assert "models/gemini-2.0-flash:generateContent" in captured["url"]
        assert "key=gk-test" in captured["url"]
        assert captured["body"]["generationConfig"]["responseMimeType"] == "application/json"


@pytest.mark.asyncio
class TestOpenAICompatibleProvider:
    async def test_no_auth_when_key_empty(self):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            captured["auth"] = request.headers.get("authorization")
            captured["body"] = json.loads(request.content)
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"findings": [], "ai_score": 90, "ai_summary": "ok"}
                                )
                            }
                        }
                    ]
                },
            )

        provider = OpenAICompatibleProvider(
            AIConfig(
                provider="openai-compatible",
                api_key="",
                base_url="http://localhost:11434/v1",
                model="llama3.2",
            )
        )
        async with _mock_client(handler) as client:
            await provider.complete("sys", "usr", SCHEMA, client=client)

        assert captured["auth"] is None
        assert captured["body"]["model"] == "llama3.2"
        # response_format is not forced for local endpoints (some don't support it)
        assert "response_format" not in captured["body"]


def test_build_provider_dispatch():
    assert isinstance(
        build_provider(AIConfig(provider="openai", api_key="x")), OpenAIProvider
    )
    assert isinstance(
        build_provider(AIConfig(provider="anthropic", api_key="x")),
        AnthropicProvider,
    )
    assert isinstance(
        build_provider(AIConfig(provider="gemini", api_key="x")), GeminiProvider
    )
    assert isinstance(
        build_provider(AIConfig(provider="openai-compatible")),
        OpenAICompatibleProvider,
    )
