# Bactester Engine

Backtesting engine for crypto strategies using Binance 1-minute candle data.

## Features

- Binance 1m OHLCV fetcher with pagination (up to 1000 candles per request)
- CSV-backed historical data stored in `data/`
- Event-driven backtesting engine with configurable fees / slippage
- Strategy plugin system (`backend/strategies/`)
- First strategy: **Ladder Bot** (DCA-style laddered entries with pooled take-profit)
- FastAPI backend exposing `/strategies`, `/backtest`, `/data`
- React panel for strategy configuration and equity-curve visualisation

## Quick start

### 1. Install backend

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

### 2. Fetch data (already committed for BTCUSDT 30d)

```bash
python -m scripts.fetch_data --symbol BTCUSDT --days 30 --interval 1m
```

### 3. Run backend

```bash
uvicorn backend.main:app --reload --port 8000
```

### 4. Run frontend

```bash
cd frontend
npm install
npm run dev
```

Open http://localhost:5173

## Project layout

```
backend/
  data/          # Binance fetcher + CSV loader
  engine/        # Backtest loop, broker, metrics
  strategies/    # Strategy implementations (base + ladder_bot)
  api/           # FastAPI routes
  main.py        # FastAPI app entry
data/            # Committed historical candles (CSV)
frontend/        # React + Vite UI
scripts/         # CLI helpers (fetch_data)
```

## Adding a new strategy

1. Create `backend/strategies/<name>.py` subclassing `Strategy`.
2. Expose a Pydantic params model in the file.
3. Register in `backend/strategies/__init__.py`.
4. Add a config panel in `frontend/src/components/`.
