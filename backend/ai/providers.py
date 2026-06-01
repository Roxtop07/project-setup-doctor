from __future__ import annotations

import json
import logging
from typing import Any, Optional, Protocol

import httpx

from ai.config import AIConfig

logger = logging.getLogger(__name__)


class AIProviderError(RuntimeError):
    """Raised when a provider call fails or returns unparseable output."""


class AIProvider(Protocol):
    async def complete(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        ...


def _extract_first_json_object(text: str) -> dict[str, Any]:
    """Best-effort: pull the first {...} block out of a string and parse it.

    Models sometimes wrap JSON in prose or fences even when told not to.
    """
    text = text.strip()
    if text.startswith("```"):
        # strip ```json ... ```
        text = text.strip("`")
        if text.lower().startswith("json"):
            text = text[4:]
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        raise AIProviderError("Provider response did not contain JSON")
    try:
        return json.loads(text[start : end + 1])
    except json.JSONDecodeError as e:
        raise AIProviderError(f"Provider response was not valid JSON: {e}") from e


class _BaseHTTPProvider:
    def __init__(self, config: AIConfig) -> None:
        self.config = config

    async def _post(
        self,
        url: str,
        headers: dict[str, str],
        body: dict[str, Any],
        client: Optional[httpx.AsyncClient],
    ) -> httpx.Response:
        timeout = self.config.timeout_seconds
        if client is not None:
            response = await client.post(url, headers=headers, json=body, timeout=timeout)
        else:
            async with httpx.AsyncClient(timeout=timeout) as owned:
                response = await owned.post(url, headers=headers, json=body)
        if response.status_code >= 400:
            raise AIProviderError(
                f"Provider HTTP {response.status_code}: {response.text[:300]}"
            )
        return response


class OpenAIProvider(_BaseHTTPProvider):
    async def complete(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        url = f"{self.config.effective_base_url().rstrip('/')}/chat/completions"
        headers = {
            "Authorization": f"Bearer {self.config.api_key}",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.effective_model(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.2,
        }
        response = await self._post(url, headers, body, client)
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise AIProviderError(f"Malformed OpenAI response: {e}") from e
        return _extract_first_json_object(content)


class AnthropicProvider(_BaseHTTPProvider):
    async def complete(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        base = self.config.effective_base_url().rstrip("/")
        # Anthropic's public endpoint is /v1/messages; users may pass either form.
        if base.endswith("/v1"):
            url = f"{base}/messages"
        else:
            url = f"{base}/v1/messages"
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json",
        }
        body = {
            "model": self.config.effective_model(),
            "max_tokens": 2048,
            "system": system,
            "messages": [
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        response = await self._post(url, headers, body, client)
        data = response.json()
        try:
            blocks = data["content"]
            text_parts = [b.get("text", "") for b in blocks if b.get("type") == "text"]
            content = "".join(text_parts)
        except (KeyError, TypeError) as e:
            raise AIProviderError(f"Malformed Anthropic response: {e}") from e
        return _extract_first_json_object(content)


class GeminiProvider(_BaseHTTPProvider):
    async def complete(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        base = self.config.effective_base_url().rstrip("/")
        model = self.config.effective_model()
        url = (
            f"{base}/models/{model}:generateContent?key={self.config.api_key}"
        )
        headers = {"Content-Type": "application/json"}
        body = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": [{"role": "user", "parts": [{"text": user}]}],
            "generationConfig": {
                "temperature": 0.2,
                "responseMimeType": "application/json",
            },
        }
        response = await self._post(url, headers, body, client)
        data = response.json()
        try:
            candidates = data["candidates"]
            parts = candidates[0]["content"]["parts"]
            content = "".join(p.get("text", "") for p in parts)
        except (KeyError, IndexError, TypeError) as e:
            raise AIProviderError(f"Malformed Gemini response: {e}") from e
        return _extract_first_json_object(content)


class OpenAICompatibleProvider(OpenAIProvider):
    """OpenAI-compatible endpoint (Ollama, LM Studio, vLLM, etc.).

    Identical wire format; api_key may be empty.
    """

    async def complete(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        client: Optional[httpx.AsyncClient] = None,
    ) -> dict[str, Any]:
        url = f"{self.config.effective_base_url().rstrip('/')}/chat/completions"
        headers = {"Content-Type": "application/json"}
        if self.config.api_key:
            headers["Authorization"] = f"Bearer {self.config.api_key}"
        body = {
            "model": self.config.effective_model(),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.2,
        }
        response = await self._post(url, headers, body, client)
        data = response.json()
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError, TypeError) as e:
            raise AIProviderError(f"Malformed OpenAI-compatible response: {e}") from e
        return _extract_first_json_object(content)


def build_provider(config: AIConfig) -> AIProvider:
    if config.provider == "openai":
        return OpenAIProvider(config)
    if config.provider == "anthropic":
        return AnthropicProvider(config)
    if config.provider == "gemini":
        return GeminiProvider(config)
    if config.provider == "openai-compatible":
        return OpenAICompatibleProvider(config)
    raise AIProviderError(f"Unknown provider: {config.provider}")
