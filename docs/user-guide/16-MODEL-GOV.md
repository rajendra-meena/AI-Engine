# Model Governance Center

## Purpose

The Model Governance Center manages the **AI models** that make trading decisions. It tracks which model is currently in use (the "Champion"), which models are being tested (the "Challengers"), and whether a model should be promoted, rejected, or rolled back.

**Think of it like a sports team.** The Champion is the starting player. The Challenger is the rookie trying to earn a spot. The coach (you) decides who plays based on performance data.

---

## Who Should Use It

| User | Why |
|---|---|
| **Advanced** | To manage AI model lifecycle |
| **Administrators** | To approve or reject model changes |

---

## Key Concepts

### Model Status

Every model goes through these stages:

| Status | Meaning |
|---|---|
| **Draft** | New model, not yet tested |
| **Validation** | Being tested |
| **Candidate** | Ready to try out |
| **Challenger** | Actively competing with Champion |
| **Champion** | Currently in use — makes real decisions |
| **Archived** | Retired |
| **Rolled Back** | Was Champion, then removed |

### Champion

The **Champion** is the model currently making trading decisions.

- Only the Champion can influence real trades
- The Champion has passed all validation tests
- The Champion is constantly monitored for performance

### Challenger

A **Challenger** is a new model being tested alongside the Champion.

- The Challenger receives the same market data
- The Challenger makes predictions but does NOT execute trades
- The Challenger is compared against the Champion

**Why have Challengers?** To test improvements without risking your money.

---

## Walk-Forward Validation

Before a Challenger can become Champion, it must pass **Walk-Forward Validation**:

1. **Train** the model on old data
2. **Test** on newer data
3. **Repeat** across multiple time periods
4. **Check** if performance is consistent

**Passing means:** The model works not just on old data, but on new data too.

---

## Side-by-Side Comparison

The system compares Champion vs Challenger on:

| Metric | What It Compares |
|---|---|
| Win Rate | Who wins more often? |
| Sharpe Ratio | Who has better risk-adjusted returns? |
| Drawdown | Who loses less during bad periods? |
| Confidence | Who calibrates better? |
| Profit Factor | Who makes more per rupee risked? |

---

## Promotion Checklist

Before promoting a Challenger to Champion, the system checks:

| Check | Requirement |
|---|---|
| Minimum trades | Challenger must have at least 30 trades |
| Better Sharpe | Challenger must have better risk-adjusted returns |
| Stable drawdown | Challenger's losses must not be much worse |
| Walk-forward pass | Must score at least 60% in walk-forward tests |
| Good calibration | Confidence must match reality |
| Profit factor | Must be at least as good as Champion |

**Human review is always required.** The system recommends, but a person decides.

---

## Rollback

If a Champion performs poorly, you can **rollback** to a previous Champion.

**Rules:**
- Rollbacks are NEVER automatic
- Always requires human approval
- Full audit trail is maintained
- Previous Champion is restored

---

## Model Lineage

The system tracks the **family tree** of every model:

- Which model was it derived from?
- What was changed?
- When was it trained?
- What data was used?
- Who approved it?

This ensures complete transparency.

---

## Common Mistakes

| Mistake | Why |
|---|---|
| Promoting without enough trades | 30 trades minimum — less is not statistically meaningful |
| Ignoring drawdown | A model with high returns but high drawdown is risky |
| Auto-promoting | Always require human review |
| Not tracking lineage | You need to know how models evolved |

---

## Related Pages

- [AI Performance →](13-AI-PERFORMANCE.md)
- [Production Readiness →](19-PRODUCTION.md)
- [Certification →](17-CERTIFICATION.md)
