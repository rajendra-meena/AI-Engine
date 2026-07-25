"""
AI Orchestrator — Manages multiple AI providers with automatic fallback.

Supported providers:
- Claude (Anthropic)
- OpenAI (GPT-4, GPT-3.5)
- Gemini (Google)
- DeepSeek
- OpenRouter
"""

from __future__ import annotations

import asyncio
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

logger = logging.getLogger(__name__)


class AIProvider(str, Enum):
    CLAUDE = "claude"
    OPENAI = "openai"
    GEMINI = "gemini"
    DEEPSEEK = "deepseek"
    OPENROUTER = "openrouter"


PROVIDER_PRIORITY = [
    AIProvider.CLAUDE,
    AIProvider.OPENAI,
    AIProvider.GEMINI,
    AIProvider.DEEPSEEK,
    AIProvider.OPENROUTER,
]


@dataclass
class AIRequest:
    prompt: str
    system_prompt: Optional[str] = None
    model: Optional[str] = None
    max_tokens: int = 4096
    temperature: float = 0.7
    timeout_seconds: int = 30


@dataclass
class AIResponse:
    content: str
    provider: AIProvider
    model: str
    tokens_in: int = 0
    tokens_out: int = 0
    cost: float = 0.0
    latency_ms: float = 0.0
    success: bool = True
    error: Optional[str] = None


@dataclass
class AICostMetrics:
    total_tokens: int = 0
    total_cost: float = 0.0
    total_requests: int = 0
    failed_requests: int = 0
    average_latency_ms: float = 0.0
    provider_usage: dict[str, int] = field(default_factory=dict)


class AIOrchestrator:
    """
    Manages AI provider calls with automatic fallback, retry, and cost tracking.

    Provider priority: Claude > OpenAI > Gemini > DeepSeek > OpenRouter
    """

    def __init__(self):
        self._metrics = AICostMetrics()
        self._health: dict[str, bool] = {p.value: True for p in AIProvider}

    async def complete(
        self, request: AIRequest, provider: Optional[AIProvider] = None
    ) -> AIResponse:
        """Send a completion request with automatic fallback."""
        providers = [provider] if provider else PROVIDER_PRIORITY
        last_error = None

        for p in providers:
            if not self._health.get(p.value, False):
                continue

            try:
                start = time.monotonic()
                response = await self._call_provider(p, request)
                elapsed = (time.monotonic() - start) * 1000
                response.latency_ms = elapsed

                self._track_metrics(p, response)
                return response

            except Exception as e:
                last_error = e
                self._health[p.value] = False
                logger.warning(
                    f"Provider {p.value} failed: {e}. Trying next provider..."
                )
                continue

        return AIResponse(
            content="",
            provider=providers[-1],
            model="",
            success=False,
            error=str(last_error or "All providers failed"),
        )

    async def stream(self, request: AIRequest, provider: Optional[AIProvider] = None):
        """Stream a completion response."""
        p = provider or PROVIDER_PRIORITY[0]
        async for chunk in self._stream_provider(p, request):
            yield chunk
        self._metrics.total_requests += 1

    def get_health(self) -> dict[str, bool]:
        return dict(self._health)

    def get_metrics(self) -> AICostMetrics:
        return self._metrics

    def reset_health(self, provider: Optional[AIProvider] = None):
        if provider:
            self._health[provider.value] = True
        else:
            for p in AIProvider:
                self._health[p.value] = True

    async def _call_provider(
        self, provider: AIProvider, request: AIRequest
    ) -> AIResponse:
        """Call a specific AI provider (stub — replace with actual API calls)."""
        await asyncio.sleep(0.1)
        return AIResponse(
            content=f"Response from {provider.value}",
            provider=provider,
            model=request.model or f"{provider.value}-default",
            tokens_in=100,
            tokens_out=50,
            cost=0.001,
        )

    async def _stream_provider(self, provider: AIProvider, request: AIRequest):
        """Stream from provider (stub — replace with actual streaming)."""
        yield f"data: {{{{ Streaming from {provider.value} }}}}\n\n"
        yield "data: [DONE]\n\n"

    def _track_metrics(self, provider: AIProvider, response: AIResponse):
        self._metrics.total_requests += 1
        if not response.success:
            self._metrics.failed_requests += 1
        self._metrics.total_tokens += response.tokens_in + response.tokens_out
        self._metrics.total_cost += response.cost
        self._metrics.provider_usage[provider.value] = (
            self._metrics.provider_usage.get(provider.value, 0) + 1
        )
        n = self._metrics.total_requests
        self._metrics.average_latency_ms = (
            self._metrics.average_latency_ms * (n - 1) + response.latency_ms
        ) / n
