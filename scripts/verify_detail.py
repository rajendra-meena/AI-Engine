"""Runtime verification - detailed checks"""
import json
import sys
import urllib.request
import urllib.error

BASE = "http://127.0.0.1:8000"

def api(path):
    try:
        r = urllib.request.urlopen(f"{BASE}{path}", timeout=15)
        return json.loads(r.read())
    except urllib.error.HTTPError as e:
        return {"_error": f"HTTP {e.code}"}
    except Exception as e:
        return {"_error": str(e)}

# 1. Candle data
print("=== INTRADAY DATA ===")
data = api("/api/intraday?symbol=NIFTY%2050&interval=15m&days=3")
candles = data.get("candles", [])
print(f"Candles: {len(candles)}")
for c in candles[-3:]:
    t = c.get("time","")
    print(f"  {t} O={c['open']} H={c['high']} L={c['low']} C={c['close']} V={c['volume']}")

print()

# 2. Indicator data
print("=== INDICATORS ===")
ind = api("/api/indicators/latest?symbol=NIFTY%2050&interval=15m")
print(json.dumps(ind, indent=2)[:1000])

print()

# 3. Candle engine status
print("=== CANDLE ENGINE ===")
ce = api("/api/candles/status")
print(json.dumps(ce, indent=2)[:500])

print()

# 4. Auto trade workspace
print("=== AUTO TRADE WORKSPACE ===")
ws = api("/api/auto-trade/workspace")
print(json.dumps(ws, indent=2)[:2000])
