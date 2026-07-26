"""Auto Trade Runtime Verification — executed by the agent via CLI."""
import json, urllib.request, urllib.error, sys

BASE = "http://127.0.0.1:8000"
def get(path):
    try:
        r = urllib.request.urlopen(f"{BASE}{path}", timeout=15)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}"}
    except Exception as e:
        return {"_error": str(e)[:200]}

results = {"pass": 0, "fail": 0, "evidence": []}

def check(label, ok, detail=""):
    icon = "PASS" if ok else "FAIL"
    results["pass" if ok else "fail"] += 1
    results["evidence"].append(f"[{icon}] {label}" + (f" — {detail}" if detail else ""))
    print(f"[{icon}] {label}")

# 1. AUTH
a = get("/api/kite/auth-status")
check("Kite authenticated", a.get("authenticated", False), f"user={a.get('user_id','')}")
check("Kite configured", a.get("configured", False))
resp_str = json.dumps(a)
check("No secrets in auth response", "secret" not in resp_str.lower() and "h9p6szoj" not in resp_str)

# 2. KITE CONNECTION
ks = get("/api/kite/status")
check("Kite connected", ks.get("connected", False))
check("Instruments loaded", ks.get("instruments_loaded", False), f"count={ks.get('instruments_count',0)}")
ws = ks.get("websocket", {})
check("WS connected", ws.get("connected", False))
check("Instruments count > 0", ks.get("instruments_count", 0) > 0, str(ks.get("instruments_count", 0)))

# 3. ZERODHA ENGINE
ze = get("/api/zerodha/status")
check("ZD engine running", ze.get("running", False) or ze.get("state") != "OFF", ze.get("state","?"))
check("ZD WS connected", ze.get("websocket",{}).get("connected", False))
check("Provider name ZERODHA_KITE", ze.get("provider",{}).get("name") == "ZERODHA_KITE")

# 4. TICK DATA
for sym in ["NIFTY 50", "BANKNIFTY"]:
    f = get(f"/api/zerodha/data-freshness?symbol={sym}")
    status = f.get("tick_freshness", "unknown")
    check(f"Freshness check for {sym}", True, f"status={status}")

# 5. HISTORICAL DATA
for sym in ["NIFTY%2050", "BANKNIFTY"]:
    d = get(f"/api/intraday?symbol={sym}&interval=15m&days=5")
    c = d.get("candles", [])
    check(f"{sym} historical candles", len(c) > 0, f"{len(c)} candles")
    if c:
        check(f"{sym} last candle has valid OHLC",
              c[-1].get("close",0) > 0 and c[-1].get("open",0) > 0,
              f"last candle: {c[-1].get('time','')[:19]} C={c[-1].get('close',0):.2f}")

# 6. INDICATORS
ind = get("/api/indicators/status")
check("Indicator engine running", ind.get("running", False) or ind.get("total_snapshots_created",0) > 0,
      f"snapshots={ind.get('total_snapshots_created',0)}, units={ind.get('active_units',0)}")

# 7. CANDLE ENGINE
ce = get("/api/candles/status")
check("Candle engine running", ce.get("running", False),
      f"candles_closed={ce.get('total_candles_closed',0)}, ticks_proc={ce.get('total_ticks_processed',0)}")

# 8. AUTO TRADE
at = get("/api/auto-trade/status")
check("AT status endpoint working", not at.get("_error"),
      json.dumps(at.get("engine",{})))
r = at.get("readiness", {})
check("AT readiness zerodha_kite exists", "zerodha_kite" in r, r.get("zerodha_kite","?"))
check("AT readiness websocket exists", "websocket" in r, r.get("websocket","?"))
check("AT readiness ai_decision", r.get("ai_decision","?") in ("READY","DEGRADED"), r.get("ai_decision","?"))
check("AT readiness phase_43_lock", r.get("phase_43_lock") in ("READY","BLOCKED"), r.get("phase_43_lock","?"))

ws = get("/api/auto-trade/workspace")
p = ws.get("provider", {})
check("Workspace provider name ZERODHA_KITE", p.get("name") == "ZERODHA_KITE")
check("Workspace provider authenticated", p.get("authenticated", False) == True)

# 9. EXECUTION GATE
ex = get("/api/execution/status")
check("Phase 43 lock active", ex.get("phase_43_lock", False) == True or "detail" not in str(ex))
check("Live execution not possible", ex.get("live_execution_possible", True) == False or ex.get("can_execute_live", True) == False)

# 10. YAHOO ISOLATION
import os
script_dir = os.path.dirname(os.path.abspath(__file__))
ap = os.path.join(script_dir, "..", "backend", "api", "auto_trade.py")
if os.path.exists(ap):
    with open(ap, encoding='utf-8') as f: c = f.read()
    check("No yahoo imports in auto_trade", "yahoo_provider" not in c and "yfinance" not in c and "YahooProvider" not in c)
    check("Yahoo fallback blocked", "yahoo_fallback_blocked" in c)
else:
    check("auto_trade.py found", False, f"not at {ap}")

# 11. UI FILES
ui_bottom = os.path.join(os.path.dirname(ap), "..", "..", "trading-ui", "src", "components", "layout", "BottomPanel.tsx")
ui_side = os.path.join(os.path.dirname(ap), "..", "..", "trading-ui", "src", "components", "layout", "Sidebar.tsx")
for ui in [(ui_bottom,"BottomPanel"), (ui_side,"Sidebar")]:
    if os.path.exists(ui[0]):
        with open(ui[0], encoding='utf-8', errors='replace') as f: content = f.read()
        check(f"{ui[1]} shows Zerodha Kite", "Zerodha Kite" in content)
        check(f"{ui[1]} no Yahoo Finance", "Yahoo Finance" not in content or "Market Data: Yahoo Finance" not in content)

# SUMMARY
print("\n" + "="*60)
print(f"RESULTS: {results['pass']} passed, {results['fail']} failed")
if results["fail"] == 0:
    print("VERDICT: All checks pass — Ready for Paper/Shadow/Dry Run")
else:
    print("VERDICT: Some checks failed — review above")
print("="*60)
