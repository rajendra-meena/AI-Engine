"""
Market Intelligence API routes.

/api/intelligence/economic-calendar
/api/intelligence/news
/api/intelligence/institutional-flow
/api/intelligence/options
/api/intelligence/sectors
/api/intelligence/regime
"""

import random
from datetime import datetime, timedelta
from fastapi import APIRouter, Query

router = APIRouter(tags=["intelligence"])

# ── Helper ──


def _random_float(min_v: float, max_v: float) -> float:
    return round(min_v + random.random() * (max_v - min_v), 2)


# ── Routes ──


@router.get("/api/intelligence/economic-calendar")
async def economic_calendar(country: str = "", from_date: str = "", to_date: str = ""):
    events = []
    names = [
        "Interest Rate Decision",
        "CPI Data",
        "GDP Growth",
        "Employment Change",
        "FOMC Minutes",
        "RBI Repo Rate",
        "Industrial Production",
        "Retail Sales",
    ]
    countries = ["US", "IN", "UK", "EU", "JP", "CN"]
    for i in range(10):
        events.append(
            {
                "id": f"econ_{i}",
                "title": random.choice(names),
                "country": country or random.choice(countries),
                "date": (
                    datetime.utcnow() + timedelta(days=random.randint(0, 30))
                ).isoformat(),
                "impact": random.choice(["high", "medium", "low"]),
                "previous": str(_random_float(-2, 5)),
                "forecast": str(_random_float(-2, 5)),
                "actual": None,
                "currency": "INR",
                "affectedAssets": [f"ASSET_{i}"],
                "riskRating": random.choice(["low", "medium", "high"]),
            }
        )
    return events


@router.get("/api/intelligence/news")
async def news_intelligence(symbol: str = "", category: str = "", limit: int = 20):
    items = []
    sentiments = ["positive", "negative", "neutral"]
    sources = [
        "Bloomberg",
        "Reuters",
        "CNBC",
        "Economic Times",
        "Mint",
        "Business Standard",
    ]
    for i in range(min(limit, 15)):
        items.append(
            {
                "id": f"news_{i}",
                "title": f"Market Update: {symbol or 'NIFTY 50'} shows mixed signals amid global uncertainty",
                "summary": f"Analysis of current market conditions for {symbol or 'NIFTY 50'} with focus on institutional activity and technical levels.",
                "source": random.choice(sources),
                "category": category or "market",
                "sentiment": random.choice(sentiments),
                "sentimentScore": _random_float(-1, 1),
                "confidence": _random_float(60, 95),
                "importance": random.choice(["high", "medium", "low"]),
                "expectedImpact": random.choice(["positive", "negative", "neutral"]),
                "marketBias": random.choice(["bullish", "bearish", "neutral"]),
                "url": "https://example.com/news",
                "publishedAt": (
                    datetime.utcnow() - timedelta(hours=random.randint(0, 24))
                ).isoformat(),
            }
        )
    return items


@router.get("/api/intelligence/institutional-flow")
async def institutional_flow(symbol: str = ""):
    return {
        "date": datetime.utcnow().isoformat(),
        "fiiBuy": _random_float(5000, 15000),
        "fiiSell": _random_float(3000, 12000),
        "fiiNet": _random_float(-3000, 5000),
        "diiBuy": _random_float(3000, 10000),
        "diiSell": _random_float(2000, 8000),
        "diiNet": _random_float(-2000, 4000),
        "deliveryPercent": _random_float(25, 45),
        "blockDeals": [],
        "bulkDeals": [],
    }


@router.get("/api/intelligence/options")
async def options_intelligence(symbol: str = "NIFTY 50"):
    return {
        "symbol": symbol,
        "expiry": (datetime.utcnow() + timedelta(days=7)).isoformat(),
        "pcr": _random_float(0.7, 1.3),
        "maxPain": _random_float(19000, 20000),
        "iv": _random_float(12, 25),
        "ivRank": _random_float(20, 80),
        "ivPercentile": _random_float(25, 75),
        "oiBuildUp": [
            {
                "strike": s,
                "type": random.choice(["ce", "pe"]),
                "oi": int(_random_float(100000, 500000)),
                "change": int(_random_float(-10000, 10000)),
            }
            for s in range(19000, 20100, 100)
        ],
        "gammaExposure": _random_float(-50, 50),
        "dealerPositioning": random.choice(["long_gamma", "short_gamma", "neutral"]),
    }


@router.get("/api/intelligence/sectors")
async def sector_intelligence():
    sectors = [
        "IT",
        "Banking",
        "Pharma",
        "Auto",
        "FMCG",
        "Energy",
        "Metal",
        "Realty",
        "PSU",
        "Media",
    ]
    return [
        {
            "name": s,
            "change": _random_float(-3, 3),
            "relativeStrength": _random_float(0.5, 1.5),
            "momentum": _random_float(-2, 2),
            "trend": random.choice(["uptrend", "downtrend", "ranging"]),
            "leadership": _random_float(0, 100),
            "capitalRotation": _random_float(-50, 50),
        }
        for s in sectors
    ]


@router.get("/api/intelligence/regime")
async def market_regime():
    return {
        "regime": random.choice(
            ["GROWTH", "RISK_ON", "RISK_OFF", "DEFENSIVE", "RECOVERY"]
        ),
        "volatility": random.choice(["LOW", "NORMAL", "HIGH", "EXTREME"]),
        "breadth": _random_float(30, 80),
        "correlation": _random_float(0.2, 0.8),
        "riskOn": random.random() > 0.5,
    }
