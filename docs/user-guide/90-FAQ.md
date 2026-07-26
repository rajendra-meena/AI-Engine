# Frequently Asked Questions

## Getting Started

**Q: What is MarketMind AI?**
A: It's a smart trading assistant that watches the market for you, makes trading decisions, and helps you avoid mistakes. It's like having an expert trader sitting next to you 24/7.

**Q: Do I need trading experience?**
A: No. The system is designed for complete beginners. The AI does the analysis — you just need to understand what it tells you.

**Q: Is this real trading?**
A: It can be. You can start with paper trading (fake money), then move to controlled live trading (real money with strict limits).

**Q: How much money do I need to start?**
A: For paper trading, zero — it's fake money. For live trading, you need a Zerodha account.

**Q: What is a Zerodha account?**
A: Zerodha is India's largest stock broker. You need an account with them to place real trades.

---

## AI & Decisions

**Q: What is Confidence?**
A: It's how sure the AI is about its decision. 80% means the AI is 80% sure. Think of it like a weather forecast — 80% chance of rain means you should probably take an umbrella.

**Q: Why did the AI say NO TRADE?**
A: The AI says NO TRADE when conditions aren't favorable. This could be because confidence is too low, risk is too high, or the market doesn't have a clear direction. NO TRADE is a valid and smart decision.

**Q: Can the AI be wrong?**
A: Yes. No AI is 100% accurate. The AI might lose trades. That's why risk management exists — to make sure one bad trade doesn't hurt too much.

**Q: What is a Trade Grade?**
A: The AI grades each trade opportunity like a school report card: A+, A, B, C, D, or REJECT. Higher grades mean better setups.

**Q: Why did the AI change its mind?**
A: Market conditions change constantly. New price data can change the AI's analysis. This is normal.

**Q: What is the difference between BUY and SELL?**
A: BUY means the AI expects the price to go up. SELL means the AI expects the price to go down.

---

## Risk

**Q: Why did Risk become Red?**
A: Risk turns red when the system detects dangerous conditions — high volatility, large daily losses, or market instability. When risk is red, you should not trade.

**Q: What is the Kill Switch?**
A: A big red button that stops ALL trading immediately. Use it in emergencies.

**Q: What is Drawdown?**
A: Drawdown is how much your account has fallen from its highest point. If you had ₹1,00,000 and now have ₹85,000, your drawdown is 15%.

**Q: What is Daily Loss Limit?**
A: The maximum amount you can lose in one day. When you hit this limit, trading stops automatically.

**Q: Can I disable the risk engine?**
A: No. The risk engine always runs. It's your safety net.

---

## Market Regime

**Q: What is a Market Regime?**
A: It's the current "personality" of the market — is it trending up, trending down, moving sideways, or acting crazy? Different regimes need different strategies.

**Q: What is a Strong Bull Trend?**
A: The market is going up strongly and consistently. This is good for buying.

**Q: What is a Sideways Range?**
A: The price is bouncing between two levels without going anywhere. It's like a room with a floor and ceiling.

**Q: What is High Volatility?**
A: Prices are moving a lot, very quickly. This creates opportunities but also higher risk.

**Q: What is an Illiquid Market?**
A: Very few people are trading. This makes it hard to enter or exit trades at good prices.

**Q: Why does the regime matter?**
A: Different market conditions need different strategies. Using the wrong strategy for the current regime is a common cause of losses.

---

## Trading

**Q: What is Paper Trading?**
A: Trading with fake money using real market prices. You learn without risking anything.

**Q: What is Controlled Live Trading?**
A: Real trading with strict limits — max 1 share and ₹10,000 per trade.

**Q: What is an SL (Stop Loss)?**
A: A price level where the trade automatically closes if it goes against you. It limits your loss.

**Q: What is a Target?**
A: The price level where you expect to take profit. The trade closes automatically when it hits target.

**Q: What is Risk/Reward Ratio?**
A: How much you could lose compared to how much you could gain. A 1:2 ratio means risking ₹1 to make ₹2.

**Q: Why was my order blocked?**
A: Orders can be blocked for many reasons: risk too high, confidence too low, daily loss reached, or safety checks failed.

**Q: What is a MARKET order?**
A: An order that executes immediately at the current market price. In Controlled Live, only MARKET orders are allowed.

---

## Models

**Q: What is the Champion Model?**
A: The AI model currently making trading decisions. It's the "best" model that has passed all tests.

**Q: What is a Challenger Model?**
A: A new model being tested alongside the Champion. It makes predictions but doesn't execute trades.

**Q: What is Model Rollback?**
A: Switching back to a previous model if the current one performs poorly.

**Q: What is Walk-Forward Validation?**
A: A testing method that trains a model on old data and tests it on new data, repeated across multiple time periods.

---

## System

**Q: What is Replay Mode?**
A: A mode that lets you play back historical market data. Useful for testing strategies.

**Q: What is the Canary?**
A: A small, low-risk test trade before full rollout. Named after the "canary in a coal mine" — if it survives, things are safe.

**Q: What is the Event Bus?**
A: The internal messaging system that carries information between different parts of the platform.

**Q: What is a WebSocket?**
A: A technology that pushes live data to your screen instantly, without you needing to refresh.

---

## Troubleshooting

**Q: Why is data stale?**
A: The market data feed may be disconnected. Check your internet connection and the Command Center.

**Q: Why is the AI not responding?**
A: The AI engine might be starting up or processing new data. Wait a few seconds and refresh.

**Q: Why is the chart not loading?**
A: Market data may not be available (weekends, holidays, or after market hours).

**Q: What should I do if something seems wrong?**
A: Check the Command Center first, then the Risk Center. If needed, activate the Kill Switch.

---

## Best Practices

**Q: How many trades should I take per day?**
A: Quality over quantity. 1-2 good trades are better than 10 mediocre ones.

**Q: Should I always trust the AI?**
A: The AI is a tool, not a crystal ball. Use it as guidance, but always apply your own judgment.

**Q: What should I do after a losing trade?**
A: Review it in the AI Performance Center. Understand what went wrong. Don't revenge trade.

**Q: When should I review my performance?**
A: Daily for quick checks. Weekly for detailed analysis. Monthly for strategy review.

**Q: How do I get better?**
A: Use Replay mode to practice. Review your trades. Read the AI's reasoning. Learn from mistakes.
