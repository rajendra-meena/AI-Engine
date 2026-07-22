# MarketMind AI — AI Providers Guide

## Architecture

The AI Orchestrator manages multiple AI providers with automatic fallback.

```
┌──────────────────┐
│  AI Orchestrator  │
│  (fallback, retry) │
└──────┬───────────┘
       │
  ┌────┼────┬────┬────┐
  ▼    ▼    ▼    ▼    ▼
Claude OpenAI Gemini DeepSeek OpenRouter
```

## Provider Priority

The orchestrator tries providers in this order, falling back on failure:

1. **Claude** (Anthropic) — Default for trading analysis
2. **OpenAI** — Fallback
3. **Gemini** (Google) — Fallback
4. **DeepSeek** — Fallback
5. **OpenRouter** — Final fallback

## Configuration

Set environment variables for each provider:

```bash
# Claude (Anthropic)
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-sonnet-4-20250514

# OpenAI
OPENAI_API_KEY=sk-...
OPENAI_MODEL=gpt-4o

# Gemini
GEMINI_API_KEY=...
GEMINI_MODEL=gemini-2.0-flash

# DeepSeek
DEEPSEEK_API_KEY=...
DEEPSEEK_MODEL=deepseek-chat

# OpenRouter
OPENROUTER_API_KEY=...
OPENROUTER_MODEL=openrouter/auto
```

## Features

- **Automatic Fallback**: If primary provider fails, next provider is tried
- **Retry Logic**: Each provider is retried up to 3 times
- **Timeout Control**: Configurable per-request timeout
- **Streaming Support**: SSE streaming for real-time responses
- **Token Tracking**: Per-provider token usage monitoring
- **Cost Tracking**: Accumulated cost metrics
- **Health Monitoring**: Automatic provider health detection
- **Provider Reset**: Manual or automatic provider health reset

## Usage

```python
from ai_orchestrator.engine import AIOrchestrator, AIRequest

orchestrator = AIOrchestrator()

# Simple completion
response = await orchestrator.complete(
    AIRequest(prompt="Analyze NIFTY 50 market structure")
)

# With specific provider
response = await orchestrator.complete(
    AIRequest(prompt="...", model="claude-sonnet-4-20250514"),
    provider=AIProvider.CLAUDE,
)

# Streaming
async for chunk in orchestrator.stream(AIRequest(prompt="...")):
    print(chunk)
```

## Monitoring

```python
# Get provider health
health = orchestrator.get_health()

# Get cost metrics
metrics = orchestrator.get_metrics()
print(f"Total cost: ${metrics.total_cost:.4f}")
print(f"Total tokens: {metrics.total_tokens}")
```
