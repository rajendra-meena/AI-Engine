"""Debug instrument token mapping - run this file directly."""
import os, sys, asyncio, json
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))

from providers.zerodha.kite_provider import KiteProvider
from core.symbols import list_canonical_names

async def test():
    kp = KiteProvider()
    await kp.connect()
    canonical = list_canonical_names()
    print(f'Canonical symbols ({len(canonical)}): {canonical}')
    for name in canonical:
        token = kp.instruments.map_to_kite_token(name)
        sym = kp.instruments.map_to_kite_symbol(name)
        print(f'  {name:20s}  token={str(token):10s}  kite_sym={sym}')

asyncio.run(test())
