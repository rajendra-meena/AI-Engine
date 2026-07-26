# Tooltip Reference

This document contains the official tooltip text for every interactive element in the application. These tooltips can be used as alt text, aria labels, or hover explanations.

---

## Dashboard

| Element | Tooltip |
|---|---|
| AI Decision badge | "Current AI recommendation: BUY, SELL, or NO TRADE" |
| Confidence % | "How sure the AI is about this decision. Higher = more reliable." |
| Score | "Quality of the current setup. Higher = better opportunity." |
| Risk Level badge | "Current market risk. LOW = safe, EXTREME = do not trade." |
| Refresh button | "Refresh all data on this page." |
| Symbol selector | "Choose which market symbol to analyze." |
| Regime badge | "Current market condition. Strategies perform differently in each." |
| Chart | "Price chart. Green candles = price went up. Red = price went down." |

## AI Decision Center

| Element | Tooltip |
|---|---|
| BUY signal | "AI recommends buying. Price expected to go up." |
| SELL signal | "AI recommends selling. Price expected to go down." |
| NO TRADE signal | "AI recommends waiting. Conditions not favorable." |
| Trade Grade (A+/A/B/C/D/REJECT) | "Quality score for this trade. A+ = excellent, REJECT = do not trade." |
| Approval Gate (passed) | "✅ This safety check passed." |
| Approval Gate (failed) | "❌ This safety check failed. Trade is blocked." |
| Confidence Breakdown | "10 factors that contribute to the AI's confidence score." |
| Explanation tab | "Learn why the AI made this decision in plain English." |

## Risk Center

| Element | Tooltip |
|---|---|
| Risk Score | "Overall risk level. 0-30 = safe. 70+ = dangerous." |
| Daily Loss | "How much you've lost today. Trading stops if this hits the limit." |
| Exposure | "Percentage of capital at risk in open trades." |
| Drawdown | "How far your account has fallen from its peak." |
| Kill Switch (OFF) | "🟢 Emergency stop is available but not active." |
| Kill Switch (ON) | "🔴 EMERGENCY STOP ACTIVE. All trading halted." |
| Trading Allowed (YES) | "✅ You can place trades." |
| Trading Allowed (NO) | "❌ Trading is blocked. See reasons below." |

## Market Regime Center

| Element | Tooltip |
|---|---|
| Current Regime | "What the market is doing right now (trending, ranging, etc.)" |
| Regime Confidence | "How sure the AI is about the current regime detection." |
| Stability Meter | "How stable this regime is. Higher = more reliable." |
| Transition Probability | "Chance that the regime will change soon." |
| Recommended Strategy | "Best strategy to use in the current market conditions." |
| Avoid Strategies | "Strategies likely to fail in the current market." |

## AI Performance Center

| Element | Tooltip |
|---|---|
| Overall Trade Score | "Average quality of all evaluated trades. 0-100." |
| Win Rate | "Percentage of trades that were profitable." |
| Profit Factor | "How much profit per rupee of loss. Above 1.0 is good." |
| Sharpe Ratio | "Risk-adjusted return. Higher = better." |
| Calibration Error | "How much AI confidence differs from actual results." |
| Bias (Overconfident) | "⚠️ AI thinks it's more right than it actually is." |
| Bias (Underconfident) | "AI is better than it thinks. It could trust itself more." |
| Bias (Calibrated) | "✅ AI's confidence matches reality. Ideal state." |

## Paper Trading

| Element | Tooltip |
|---|---|
| Start button | "Begin paper trading. Uses fake money with real prices." |
| Pause button | "Pause new trade generation. Existing trades continue." |
| Stop button | "Stop all paper trading activity." |
| Reset button | "Reset account to initial state (₹1,00,000)." |
| Equity | "Current total value of your paper account." |
| Available Cash | "How much paper money you can use for new trades." |

## Command Center

| Element | Tooltip |
|---|---|
| Unified Status (Healthy) | "🟢 All systems operating normally." |
| Unified Status (Degraded) | "🟡 Some systems have issues. System still operating." |
| Unified Status (Halted) | "🔴 System is stopped. Requires action to resume." |
| Data Age | "How fresh the displayed data is. Less than 5s is ideal." |
| Incident count | "Number of recent problems that need attention." |
| Block Reasons | "Why trading is currently blocked (if applicable)." |

## Model Governance

| Element | Tooltip |
|---|---|
| Champion badge | "👑 Current production model making trading decisions." |
| Challenger badge | "🧪 New model being tested alongside Champion." |
| Model Status (Draft) | "Model created but not yet tested." |
| Model Status (Champion) | "✅ Active model making trading decisions." |
| Model Status (Archived) | "💤 Retired model. No longer in use." |
| Promote button | "Promote this Challenger to Champion. Requires review." |
| Rollback button | "Revert to previous Champion. Requires human approval." |
| Walk-Forward Score | "How well the model performs on unseen data. Higher = better." |

## Production Readiness

| Element | Tooltip |
|---|---|
| Certification Score | "Percentage of subsystems that passed certification." |
| Readiness Score | "Overall production readiness. 80%+ = ready." |
| Benchmark P50 | "Typical response time for this operation." |
| Benchmark P95 | "Slow response time (worst 5% of cases)." |
| Security Score | "Percentage of security checks that passed." |
| Release Candidate | "Generated when all certification passes." |
| Approval Status | "Whether the release candidate has been approved." |

## Bottom Panel

| Element | Tooltip |
|---|---|
| Logs tab | "Real-time system log messages." |
| Orders tab | "Current order status and history." |
| Trades tab | "Recent completed trades." |
| Positions tab | "Currently open positions." |
| Executions tab | "Order execution details and latency." |
| AI Decision tab | "Current AI decision and confidence." |
| Regime tab | "Current market regime detection." |
| Risk tab | "Real-time risk metrics." |
| Alerts tab | "System alerts and warnings." |
| Live Monitor tab | "Live trading status and controls." |
| Operations tab | "System health and operations status." |
| Panel resize handle | "Drag to resize the bottom panel." |
| Minimize button | "Collapse the bottom panel." |

## General

| Element | Tooltip |
|---|---|
| Sidebar nav item | "Click to navigate to this page." |
| Sidebar collapse | "Toggle sidebar visibility." |
| Settings | "Configure your preferences." |
| Help | "View documentation and guides." |
| Theme toggle | "Switch between light and dark mode." |
| Connection status | "🟢 Connected to server. 🔴 Disconnected." |
