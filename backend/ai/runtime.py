from __future__ import annotations

from contextvars import ContextVar
from dataclasses import dataclass
from typing import Optional

from ai.config import AIConfig
from ai.providers import AIProvider


@dataclass
class AIRunMetadata:
    score: Optional[float] = None
    summary: Optional[str] = None
    model: Optional[str] = None
    provider: Optional[str] = None
    error: Optional[str] = None


# Per-request inputs (set by the API route before invoking analyzers).
current_ai_config: ContextVar[Optional[AIConfig]] = ContextVar(
    "current_ai_config", default=None
)
current_existing_issues: ContextVar[list] = ContextVar(
    "current_existing_issues", default=[]
)

# Allows tests to inject a stub provider without touching the network.
override_ai_provider: ContextVar[Optional[AIProvider]] = ContextVar(
    "override_ai_provider", default=None
)

# Output: populated by AIAnalyzer.analyze, consumed by the API route.
current_ai_metadata: ContextVar[Optional[AIRunMetadata]] = ContextVar(
    "current_ai_metadata", default=None
)
