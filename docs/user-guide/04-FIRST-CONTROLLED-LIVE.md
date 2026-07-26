# First Controlled Live Trade Guide

## What is Controlled Live Trading?

Controlled Live means the AI places **real trades** with real money, but with VERY strict limits:

- Maximum **1 share** per trade
- Maximum **₹10,000** per trade
- **20 safety checks** must ALL pass
- Human must **approve** the activation

**Think of it like driving a car with a learner's permit.** You can drive, but only with supervision and strict rules.

---

## Step 1: Understand the Prerequisites

Before you can do ANY live trading, the system checks **28 prerequisites**:

| Category | Examples |
|---|---|
| Market Data | Live feed connected. Data is fresh. |
| Broker | Connected to Zerodha. Session valid. |
| AI | Champion model active. Confidence calibrated. |
| Risk | Risk engine active. Kill switch off. |
| Operations | All systems healthy. Recovery plans ready. |

**All 28 must pass.** If even one fails, live trading stays locked.

---

## Step 2: Go to Live Activation

Click **"Live Activation"** in the sidebar.

You will see:

- **Current State:** LOCKED, READY, ARMED, or ACTIVE
- **Prerequisites:** How many passed / total
- **Action Buttons:** Validate, Arm, Start

---

## Step 3: Validate Prerequisites

Click **"Run Prerequisite Check"**.

The system checks all 28 conditions.

- ✅ = Passed
- ❌ = Failed (must fix before proceeding)

If any fail, the system tells you what to fix.

---

## Step 4: Arm the System

Once all prerequisites pass, you can **Arm** the system.

Click **"Arm LIVE"**.

You need to enter:

- **Reviewer Identity** — Your name or ID
- **Reason** — Why you are activating
- **Duration** — How long (5-60 minutes)

Arming means: "I have checked everything. I am ready for live trading."

---

## Step 5: Start Live Trading

Once armed, click **"Start LIVE"**.

You need to enter a **confirmation token** (shown during arming).

This is the final confirmation. After this:

- Live orders can be placed
- Only **1 share** at a time
- Only **₹10,000** max per trade
- Only **MARKET** orders

---

## Step 6: Place Your First Live Trade

The AI must generate a BUY or SELL signal with:

- Confidence > 80
- Trade Grade ≥ B
- All 7 approval gates passed
- Risk is LOW or MEDIUM
- 20 safety checks passed

The trade will execute through your Zerodha account.

---

## Step 7: Monitor the Trade

From the **Live Control Center**:

| Metric | What to Watch |
|---|---|
| Position | Is it open? |
| P&L | Winning or losing? |
| SL Distance | How close to stop loss? |
| Target Distance | How close to target? |

---

## Understanding Safety Layers

| Layer | What It Does |
|---|---|
| **Phase 43 Lock** | Master switch. Always ON during testing. |
| **Activation Gate** | Requires human arming + token. |
| **20-Point Check** | Every single order is checked against 20 rules. |
| **Kill Switch** | Emergency stop. Stops everything. |
| **Canary** | Small test trades before full rollout. |
| **Rollback** | Ability to undo model changes. |

---

## Important Safety Rules

| Rule | Why |
|---|---|
| Never bypass the activation gate | It exists for your protection |
| Never disable the kill switch | It is your emergency brake |
| Never ignore red risk | Red risk means stop trading |
| Never exceed position limits | Limits prevent catastrophic loss |
| Never trade during incidents | Wait until resolved |

---

## What to Do in an Emergency

If something goes wrong:

1. **Press Kill Switch** — Stops all trading immediately
2. **Check the incident** — Go to Command Center
3. **Follow recovery** — The system will guide you
4. **Do NOT restart** until the issue is resolved

---

## Related Pages

- [Live Activation →](31-LIVE-ACTIVATION.md)
- [Live Control Center →](32-LIVE-CONTROL.md)
- [Risk Center →](11-RISK.md)
- [Command Center →](20-COMMAND.md)
