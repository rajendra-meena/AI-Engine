# MarketMind AI

A standalone web application for viewing historical OHLC data of Indian market indices (NIFTY 50, BANKNIFTY, SENSEX) with AI-driven predictive analysis for the next trading day.

## Features

- **📊 Historical Data**: View OHLC data for NIFTY 50, BANKNIFTY, FINNIFTY, and SENSEX
- **📈 Interactive Charts**: Area/Line chart with SMA and Bollinger Band overlays
- **🎯 Support & Resistance**: Classic pivot points with R1-R3 and S1-S3 levels
- **🤖 AI Prediction Engine**: Rule-based technical analysis using RSI, MACD, ATR
- **📉 Next-Day Forecast**: Visual projection of predicted price movement
- **🔄 Date Range Filtering**: Quick presets (1W to 1Y) with auto-recalculation

## Tech Stack

- **Frontend**: React 19, Vite, Tailwind CSS, Recharts, Zustand
- **Backend**: Python FastAPI with yfinance
- **Data**: yfinance (Yahoo Finance, free, no API key required)

## Prerequisites

- Node.js 18+
- Python 3.9+
- pip (Python package manager)

## Setup & Running

### 1. Backend (Python FastAPI)

```bash
cd backend
pip install -r requirements.txt
uvicorn main:app --reload --port 8000
```

The backend will start at http://localhost:8000. It fetches data via Yahoo Finance (yfinance) and caches it locally as JSON files.

### 2. Frontend (React + Vite)

Open a new terminal:

```bash
cd frontend
npm install
npm run dev
```

The frontend will start at http://localhost:5173 and proxy API requests to the backend.

### 3. Open the App

Navigate to http://localhost:5173 in your browser.

## How It Works

1. **Data Fetching**: The Python backend fetches historical index data from Yahoo Finance via yfinance (free, no API key) and caches it as JSON files.
2. **Technical Analysis**: The frontend calculates RSI, MACD, ATR, SMA, and Bollinger Bands client-side.
3. **AI Prediction**: A rule-based engine scores bullish vs bearish signals and generates trade setups.
4. **Pivot Points**: Classic pivot calculation with R1-R3 and S1-S3 levels.

## Project Structure

```
marketmind-ai/
├── backend/
│   ├── main.py          # FastAPI server
│   ├── requirements.txt
│   └── cache/           # JSON data cache
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── Dashboard.jsx
│   │   │   ├── StatsCard.jsx
│   │   │   ├── MainChart.jsx
│   │   │   ├── SupportResistance.jsx
│   │   │   ├── AIPredictionCard.jsx
│   │   │   └── PredictionChart.jsx
│   │   ├── hooks/
│   │   │   └── useMarketData.js
│   │   ├── store/
│   │   │   └── useMarketStore.js
│   │   ├── utils/
│   │   │   └── technicalIndicators.js
│   │   ├── styles/
│   │   │   └── globals.css
│   │   ├── lib/
│   │   │   └── utils.js
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   ├── tailwind.config.js
│   └── postcss.config.js
└── README.md
