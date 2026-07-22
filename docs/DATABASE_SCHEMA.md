# MarketMind AI — Database Schema

## Overview

PostgreSQL database with Prisma ORM. All tables include `createdAt`, `updatedAt` timestamps and soft delete (`deletedAt`) where applicable.

## Tables

### Users & Authentication

**users** — Core user accounts
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| email | String (unique) | User email |
| passwordHash | String? | BCrypt hash |
| name | String | Display name |
| role | Enum | ADMIN, TRADER, VIEWER |
| provider | Enum | EMAIL, GOOGLE, GITHUB |
| emailVerified | Boolean | Email verified flag |
| lastLogin | DateTime | Last login timestamp |

**sessions** — JWT refresh token sessions
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID | FK → users |
| refreshToken | String (unique) | JWT refresh token |
| expiresAt | DateTime | Token expiry |

**devices** — User device management
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID | FK → users |
| name | String? | Device name |
| lastIp | String? | Last known IP |

### Trading

**trades** — Trade records
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID | FK → users |
| symbol | String | Trading symbol |
| direction | Enum | LONG, SHORT |
| entry | Float | Entry price |
| exit | Float? | Exit price |
| quantity | Int | Position size |
| pnl | Float? | Profit/loss |
| rr | Float? | Risk-reward ratio |

**orders** — Order records
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID | FK → users |
| tradeId | UUID? | FK → trades |
| symbol | String | Trading symbol |
| type | Enum | MARKET, LIMIT, STOP, etc. |
| side | String | BUY, SELL |
| quantity | Int | Order quantity |
| price | Float? | Order price |
| status | Enum | PENDING, OPEN, FILLED, etc. |
| brokerOrderId | String? | Broker's order ID |

### AI & Analysis

**predictions** — AI predictions
| Column | Type | Description |
|--------|------|-------------|
| id | Int (auto) | Primary key |
| symbol | String | Trading symbol |
| interval | String | Timeframe |
| direction | Enum | BULLISH, BEARISH, NEUTRAL |
| confidence | Float? | AI confidence |
| score | Int? | AI score |
| status | Enum | PENDING, ACTIVE, HIT, MISS |

**ai_decisions** — Full AI decision snapshots
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| symbol | String | Trading symbol |
| decision | String | Decision type |
| score | Int | Decision score |
| confidence | Int | Confidence value |
| tradePlan | JSON | Full trade plan |
| reasoning | JSON | Reasoning chain |

### User Data

**notifications** — User notifications
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID? | FK → users |
| title | String | Notification title |
| category | String | Event category |
| priority | String | INFO, SUCCESS, WARNING, CRITICAL |
| read | Boolean | Read status |

**watchlists** — User watchlists
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID | FK → users |
| name | String | Watchlist name |
| symbols | JSON | Array of symbols |

**user_settings** — User settings
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID (unique) | FK → users |
| data | JSON | Full settings object |

### Analytics & Cache

**scanner_results** — Scanner snapshots
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| symbol | String | Trading symbol |
| score | Int | AI score |
| confidence | Int | Confidence |
| risk | String | Risk level |

**market_data_cache** — Cached market data
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| symbol | String | Symbol |
| interval | String | Timeframe |
| data | JSON | Candle data |
| expiresAt | DateTime | Cache expiry |

### Audit & Logs

**audit_logs** — Security audit trail
| Column | Type | Description |
|--------|------|-------------|
| id | UUID | Primary key |
| userId | UUID? | FK → users |
| action | String | Action performed |
| resource | String | Resource affected |
| detail | JSON | Action details |
| ip | String? | Request IP |

## Indexes

- All foreign keys indexed
- `users.email` (unique)
- `sessions.refreshToken` (unique)
- All `createdAt` columns indexed for time-based queries
- Composite indexes on `(symbol, interval)` for market data
- `status` indexes for filtered queries

## Relations

```
User 1──N Session
User 1──N Device
User 1──N Trade
Trade 1──N Order
Trade 1──1 JournalEntry
User 1──N Prediction
User 1──N AIDecision
User 1──N Notification
User 1──1 Portfolio
User 1──N Watchlist
User 1──1 UserSettings
User 1──N AuditLog
```
