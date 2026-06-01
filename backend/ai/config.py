from __future__ import annotations

import os
from typing import Literal, Optional

from pydantic import BaseModel, Field

ProviderName = Literal["openai", "anthropic", "gemini", "openai-compatible"]

DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-haiku-4-5",
    "gemini": "gemini-2.0-flash",
    "openai-compatible": "llama3.2",
}

DEFAULT_BASE_URLS: dict[str, str] = {
    "openai": "https://api.openai.com/v1",
    "anthropic": "https://api.anthropic.com/v1",
    "gemini": "https://generativelanguage.googleapis.com/v1beta",
    "openai-compatible": "http://localhost:11434/v1",
}


class AIConfig(BaseModel):
    """Resolved AI configuration. Disabled when api_key is empty (except for
    openai-compatible / local providers, which can run without a key)."""

    provider: ProviderName = "openai"
    api_key: str = ""
    base_url: Optional[str] = None
    model: Optional[str] = None
    enabled: bool = True
    timeout_seconds: float = Field(default=30.0, ge=1.0, le=120.0)

    def effective_base_url(self) -> str:
        return self.base_url or DEFAULT_BASE_URLS[self.provider]

    def effective_model(self) -> str:
        return self.model or DEFAULT_MODELS[self.provider]

    def is_usable(self) -> bool:
        if not self.enabled:
            return False
        # Local / OpenAI-compatible can run without an API key.
        if self.provider == "openai-compatible":
            return True
        return bool(self.api_key)


def resolve_ai_config(request_config: Optional[AIConfig]) -> Optional[AIConfig]:
    """Resolve AI configuration with priority: request > environment.

    Returns None when no usable configuration is available so callers can skip
    AI work without further checks.
    """
    if request_config is not None and request_config.is_usable():
        return request_config

    env_provider = os.environ.get("AI_PROVIDER")
    env_key = os.environ.get("AI_API_KEY", "")
    env_base = os.environ.get("AI_BASE_URL")
    env_model = os.environ.get("AI_MODEL")

    if not env_provider:
        return None

    if env_provider not in DEFAULT_MODELS:
        return None

    cfg = AIConfig(
        provider=env_provider,  # type: ignore[arg-type]
        api_key=env_key,
        base_url=env_base,
        model=env_model,
        enabled=True,
    )
    return cfg if cfg.is_usable() else None
