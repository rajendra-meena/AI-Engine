# AI Performance Center

## Purpose

The AI Performance Center shows you **how well the AI is actually doing**. It tracks every trade the AI recommended and tells you whether those recommendations were good or bad.

**Think of it like a report card for the AI.** Just like a teacher tracks your grades, this page tracks the AI's accuracy, strengths, and weaknesses.

---

## Who Should Use It

| User | Why |
|---|---|
| **All users** | To understand if the AI can be trusted |
| **Intermediate** | To identify which strategies work best |
| **Advanced** | To fine-tune and validate AI performance |

---

## Features

### Overall Score

The page shows a single number: **Overall Trade Score** (0-100).

| Score | Meaning |
|---|---|
| 85-100 | Excellent — the AI is performing very well |
| 65-84 | Good — solid performance |
| 45-64 | Average — room for improvement |
| 25-44 | Poor — something needs to change |
| 0-24 | Failed — the AI is not working correctly |

### Outcome Distribution

Shows how many trades fell into each category:

- **Excellent** — Perfect execution
- **Good** — Solid trade
- **Average** — Could be better
- **Poor** — Below expectations
- **Failed** — Lost money

### Strategy Performance

Shows how each **strategy** is performing:

| Strategy | What It Does |
|---|---|
| Trend Following | Buy when going up, sell when going down |
| Breakout | Enter when price breaks a key level |
| Reversal | Bet that the trend will reverse |
| Pullback | Enter during a temporary move against trend |
| Range | Buy low, sell high in a range |
| Momentum | Follow strong price moves |
| Scalping | Very quick, small-profit trades |

For each strategy, you can see:
- **Win Rate** — % of trades that won
- **Profit Factor** — How much profit vs loss
- **Sharpe Ratio** — Risk-adjusted return (higher = better)

---

### Calibration (Honesty Check)

This tells you whether the AI is **honest** about its confidence:

| Bias | Meaning |
|---|---|
| ✅ Calibrated | AI's confidence matches reality. If it says 80%, it wins ~80% of the time. |
| ⚠️ Overconfident | AI thinks it is more right than it actually is. Confidence > actual accuracy. |
| ⚠️ Underconfident | AI is more accurate than it thinks. It could trust itself more. |

### Mistakes from AI

The system automatically classifies **why** losing trades lost:

| Mistake | What Happened |
|---|---|
| Late Entry | Entered after price had already moved |
| Early Exit | Exited before price reached target |
| Weak Confirmation | Took a trade with low confidence |
| False Breakout | Price broke a level then reversed |
| Wrong Trend | Traded against the market direction |
| Low Liquidity | Not enough volume to trade smoothly |
| High Slippage | Price moved before order filled |
| News Impact | Unexpected news moved the market |
| Risk Management Failure | Risked too much on one trade |

---

## Color Guide

| Metric | Green | Yellow | Red |
|---|---|---|---|
| Win Rate | Above 60% | 40-60% | Below 40% |
| Profit Factor | Above 1.5 | 1.0-1.5 | Below 1.0 |
| Sharpe | Above 1.0 | 0.5-1.0 | Below 0.5 |
| Calibration Error | Below 5% | 5-15% | Above 15% |

---

## Common Questions

**Q: The AI has a low win rate. Should I stop using it?**

Not necessarily. A 40% win rate can still be profitable if winning trades are much bigger than losing trades.

**Q: What does Profit Factor = 1.5 mean?**

For every ₹100 you risk losing, you expect to gain ₹150. Above 1.0 is profitable.

**Q: The AI is overconfident. What should I do?**

Be more skeptical of high-confidence signals. The AI thinks it's more sure than it really is.

---

## Related Pages

- [AI Decision Center →](10-AI-DECISION.md)
- [Strategy Analytics →](15-STRATEGY.md)
- [Trade Evaluation →](18-TRADE-EVAL.md)
- [Model Governance →](16-MODEL-GOV.md)
