# Production Readiness Center

## Purpose

The Production Readiness Center shows whether the system is **ready for live use**. It runs automated checks across every part of the platform and gives a single score.

**Think of it like a pre-flight checklist for an airplane.** Before taking off, the pilot checks every system. This page does the same for the trading platform.

---

## Who Should Use It

| User | Why |
|---|---|
| **Administrators** | Before enabling live trading |
| **Operators** | Daily system health verification |
| **Auditors** | Verify system integrity |

---

## Certification Tab

Shows certification results for **15 subsystems**:

| Subsystem | What's Checked |
|---|---|
| Market Data | Feed connected, candles aggregating, ticks processing |
| Replay Engine | Replay loads, speed controls work, seek works |
| AI Decision | Score engine, confidence, signal validation, trade quality |
| Strategy Router | Regime detection, strategy selection, confidence modifier |
| Risk Engine | Daily loss, exposure, drawdown checks |
| Trade Approval | All 7 approval gates functional |
| Paper Trading | Paper broker, order management, P&L tracking |
| Controlled Live | 20-point check, activation gate, kill switch |
| Operations | Recovery plans, incident manager, heartbeats |
| Model Registry | Champion exists, walk-forward, rollback |
| Regime Engine | All 14 regimes detectable, transitions logged |
| Analytics | Trade evaluation, strategy analytics, calibration |
| Database | Connected, all tables exist, indexes active |
| APIs | REST endpoints, WebSocket, response times |
| Frontend | All dashboards load, API integration, real-time updates |

---

## Readiness Checklist

Automatically verifies:

| Category | Items Checked |
|---|---|
| **Infrastructure** | Database, Event Bus, WebSocket, API Gateway, Scheduler |
| **Broker** | Login, Session, Connectivity, Permissions |
| **AI** | Champion Model, Calibration, Confidence, Dataset |
| **Operations** | Recovery, Alerting, Heartbeats, Incident Manager |
| **Deployment** | Environment variables, Secrets, TLS, Configuration |

---

## Benchmarks Tab

Shows performance measurements:

| Metric | What It Measures |
|---|---|
| P50 | Typical response time (50th percentile) |
| P95 | Slow response time (95th percentile) |
| P99 | Worst-case response time (99th percentile) |
| Max | Maximum observed response time |

**Good values:** P95 under 200ms for most operations.

---

## Security Tab

Shows results of automated security checks:

| Check | What It Verifies |
|---|---|
| Secret Leakage | No passwords in source code |
| API Authentication | All endpoints require login |
| Authorization | Users can only access what they should |
| Input Validation | All inputs are checked for safety |
| Configuration Integrity | Settings haven't been tampered with |
| Audit Immutability | Logs cannot be changed after creation |

---

## Recovery Tab

Shows fault injection test results — what happens when things break:

| Scenario | Expected Behavior |
|---|---|
| Broker Disconnect | System enters safe mode, reconnects automatically |
| Market Data Outage | Stale data flag set, catches up on reconnect |
| Database Restart | Connections re-established with retry |
| API Timeout | Retry with exponential backoff |
| Duplicate Events | Idempotency prevents double processing |
| Clock Drift | Events re-timestamped |

---

## Release Candidate

When everything passes, a **Release Candidate** is generated with:

- Version number (e.g., 1.0.0-RC1)
- Certification score
- Readiness score
- Known limitations
- Deployment checklist
- Approval status

---

## Common Mistakes

| Mistake | Why |
|---|---|
| Skipping certification | You might miss a critical issue |
| Ignoring failed checks | Each failure could cause problems |
| Deploying without readiness | The system might not be ready |
| Not running benchmarks | Performance issues might go unnoticed |

---

## Related Pages

- [Command Center →](20-COMMAND.md)
- [Model Governance →](16-MODEL-GOV.md)
- [Certification →](17-CERTIFICATION.md)
