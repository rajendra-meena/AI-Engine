# Command Center

## Purpose

The Command Center is the **mission control** for the entire trading system. It shows the health of every subsystem at a glance and lets you monitor what's happening across the platform.

**Think of it like the bridge of a ship.** The captain (you) can see if the engines are running, if there are any warnings, and whether the ship is on course.

---

## Who Should Use It

| User | Why |
|---|---|
| **All users** | Quick health check of the system |
| **Operators** | Monitor multiple subsystems |

---

## What You See

### Unified Status

| Status | Color | Meaning |
|---|---|---|
| Healthy | 🟢 Green | Everything working normally |
| Degraded | 🟡 Yellow | Some issues but still operating |
| Trading Blocked | 🔴 Red | Trading stopped, needs attention |
| Incident Active | 🔴 Red | A problem is being investigated |
| Recovery Required | 🔴 Red | System needs recovery action |
| Halted | 🔴 Red | System fully stopped |

### Data Age

Shows how fresh the displayed data is:

| Age | Color | Meaning |
|---|---|---|
| 0-5 seconds | 🟢 Green | Live data |
| 5-15 seconds | 🟡 Yellow | Slightly delayed |
| 15+ seconds | 🔴 Red | Data is stale — refresh needed |

---

## Features

### System Health

Shows the status of every major component:

| Component | What It Checks |
|---|---|
| Market Data | Is price data flowing? |
| AI Engine | Is the AI making decisions? |
| Risk Engine | Is risk monitoring active? |
| Broker | Is the broker connected? |
| Database | Is data being stored? |
| WebSocket | Is real-time feed working? |

### Block Reasons

Shows why trading might be blocked:

- Market data is stale
- Risk score too high
- Kill switch active
- No champion model
- System in recovery

### Recent Incidents

Lists any problems that have occurred recently, with:

- What happened
- When it happened
- Whether it has been resolved

---

## Color Guide

| Component | Green | Yellow | Red |
|---|---|---|---|
| Market Data | Streaming | Delayed | Disconnected |
| AI Engine | Active | Degraded | Down |
| Risk Engine | Monitoring | Warning | Blocking |
| Broker | Connected | Slow | Disconnected |
| Database | Connected | Slow | Down |
| Data Age | < 5s | 5-15s | > 15s |

---

## When to Check Command Center

| When | Why |
|---|---|
| **Before trading** | Make sure everything is healthy |
| **If something seems wrong** | Check here first |
| **After an incident** | Verify recovery |
| **Daily startup** | Confirm all systems are operational |

---

## Related Pages

- [Risk Center →](11-RISK.md)
- [Production Readiness →](19-PRODUCTION.md)
- [Operations Center →](21-OPERATIONS.md)
