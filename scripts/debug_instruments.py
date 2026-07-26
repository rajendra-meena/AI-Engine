"""Debug instrument mapping and market data."""
import json, urllib.request, sys

BASE = "http://127.0.0.1:8000"
def g(path):
    r = urllib.request.urlopen(BASE + path, timeout=15)
    return json.loads(r.read())

# 1. Search for NIFTY 50 instrument
search = g("/api/kite/instruments/search?query=NIFTY&exchange=NSE")
print("Total search results:", search.get("count", 0))
for r in search.get("results", [])[:5]:
    print(f"  {r['tradingsymbol']} token={r['instrument_token']} seg={r.get('segment','')} type={r.get('instrument_type','')}")

# 2. Check if the mapping from internal name to Kite symbol works
# The instrument_manager maps "NIFTY 50" -> "NIFTY", then looks up "NIFTY"
# But in the search results, the symbol is "NIFTY 50" not "NIFTY"
# This is the root cause of quote/token resolution failure!

# Check what happens with the quote endpoint directly using the token
# Get tokens for indices
for sym in ["NIFTY 50", "BANKNIFTY"]:
    try:
        q = g(f"/api/kite/ltp?symbol={sym.replace(' ', '%20')}")
        print(f"LTP for {sym}: {json.dumps(q, indent=2)}")
    except Exception as e:
        print(f"LTP for {sym} error: {str(e)[:100]}")

# 3. Try direct market quote with NSE exchange prefix
for sym_trading in ["NIFTY 50", "NIFTY", "BANKNIFTY"]:
    try:
        # Try the market data REST API directly
        m = g(f"/api/market/quote?symbol={sym_trading.replace(' ', '%20')}&exchange=NSE")
        print(f"Market quote for {sym_trading}: {json.dumps(m, indent=2)[:200]}")
    except Exception as e:
        print(f"Market quote for {sym_trading} error: {str(e)[:100]}")
