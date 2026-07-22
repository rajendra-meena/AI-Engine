# MarketMind AI — API Documentation

## Base URL

Production: `https://yourdomain.com/api`
Development: `http://localhost:8000/api`

## Authentication

All API endpoints (except auth endpoints) require a Bearer JWT token.

```
Authorization: Bearer <access_token>
```

### Auth Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/auth/login` | Email/password login |
| POST | `/api/auth/register` | Create account |
| POST | `/api/auth/logout` | Invalidate tokens |
| POST | `/api/auth/refresh` | Refresh access token |
| POST | `/api/auth/forgot-password` | Send reset email |
| POST | `/api/auth/reset-password` | Reset password |
| POST | `/api/auth/verify-email` | Verify email address |
| POST | `/api/auth/send-otp` | Send OTP for login |
| POST | `/api/auth/verify-otp` | Verify OTP and login |
| POST | `/api/auth/oauth/google` | Google OAuth login |
| POST | `/api/auth/oauth/github` | GitHub OAuth login |
| GET | `/api/auth/me` | Get current user |
| GET | `/api/auth/devices` | List active devices |
| DELETE | `/api/auth/devices/:id` | Revoke device |

## Market Data

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/intraday` | Intraday candle data |
| GET | `/api/data` | Daily OHLC data |
| GET | `/api/cache/status` | Cache status |

## AI & Analysis

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/ai/latest` | Latest AI decision |
| GET | `/api/ai/status` | AI engine status |
| GET | `/api/indicators/latest` | Latest indicator values |
| GET | `/api/structure/latest` | Market structure snapshot |
| GET | `/api/patterns/latest` | Detected patterns |
| GET | `/api/context/latest` | Trading context |
| GET | `/api/sr/latest` | Support/resistance levels |
| GET | `/api/mtf/latest` | Multi-timeframe alignment |
| GET | `/api/predictions` | Prediction history |
| GET | `/api/predictions/stats` | Prediction statistics |

## Replay

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/replay/start` | Start replay session |
| POST | `/api/replay/pause` | Pause replay |
| POST | `/api/replay/resume` | Resume replay |
| POST | `/api/replay/stop` | Stop replay |
| POST | `/api/replay/seek` | Seek to position |
| POST | `/api/replay/speed` | Change speed |
| GET | `/api/replay/status` | Replay status |

## Broker

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/broker/connect` | Connect broker |
| POST | `/api/broker/place-order` | Place order |
| POST | `/api/broker/modify-order` | Modify order |
| POST | `/api/broker/cancel-order` | Cancel order |
| GET | `/api/broker/positions` | Get positions |
| GET | `/api/broker/holdings` | Get holdings |
| GET | `/api/broker/orders` | Get orders |
| GET | `/api/broker/margin` | Get margin |
| GET | `/api/broker/funds` | Get funds |

## Health

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/health` | System health |

## WebSocket

Connect to `ws://localhost:8000/ws` or `wss://yourdomain.com/ws`.

### Event Types

| Event | Channel | Description |
|-------|---------|-------------|
| `new_historical_candle` | market_data | Replay candle feed |
| `replay_*` | replay | Replay state changes |
| `ai_decision_updated` | ai | New AI decision |
| `candle_closed` | market_data | Candle closed |
| `indicator_updated` | indicators | Indicators computed |
| `structure_updated` | structure | Market structure updated |
| `pattern_detected` | patterns | Pattern detected |
| `system_status` | system | System health status |
