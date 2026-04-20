"""Generate a synthetic OHLCV dataset for offline development / CI.

Produces a CSV in the exact same schema the Binance fetcher writes, but
derived from a geometric Brownian motion with intrabar OHLC noise. Use this
only when real Binance data is unreachable (e.g. network-restricted sandbox).
"""
from __future__ import annotations

import argparse
from datetime import datetime, timedelta, timezone
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def generate(symbol: str, interval_minutes: int, days: int, seed: int = 42,
             start_price: float = 65000.0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = days * 24 * 60 // interval_minutes
    # Annualised 60% vol mapped to per-minute.
    minute_vol = 0.60 / (365 * 24 * 60) ** 0.5
    step_vol = minute_vol * (interval_minutes ** 0.5)
    returns = rng.normal(loc=0.0, scale=step_vol, size=n)
    close = start_price * np.exp(np.cumsum(returns))
    prev_close = np.concatenate([[start_price], close[:-1]])

    noise = rng.normal(loc=0.0, scale=step_vol * 0.5, size=n)
    open_ = prev_close * (1 + noise * 0.2)
    body_hi = np.maximum(open_, close)
    body_lo = np.minimum(open_, close)
    wick = np.abs(rng.normal(loc=0.0, scale=step_vol, size=n)) * prev_close
    high = body_hi + wick * 0.6
    low = body_lo - wick * 0.6

    base_volume = rng.gamma(shape=2.0, scale=1.0, size=n)  # ~2 BTC per minute typical
    volume = base_volume * (1 + np.abs(returns) * 50)
    quote_volume = volume * close
    trades = rng.integers(low=200, high=5000, size=n)

    end = datetime.now(tz=timezone.utc).replace(second=0, microsecond=0)
    start = end - timedelta(minutes=interval_minutes * n)
    timestamps = pd.date_range(start=start, periods=n, freq=f"{interval_minutes}min", tz="UTC")

    df = pd.DataFrame({
        "open_time": timestamps,
        "open": open_,
        "high": high,
        "low": low,
        "close": close,
        "volume": volume,
        "quote_volume": quote_volume,
        "trades": trades,
    })
    return df


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval-minutes", type=int, default=1)
    parser.add_argument("--days", type=int, default=30)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--start-price", type=float, default=65000.0)
    args = parser.parse_args()

    df = generate(args.symbol, args.interval_minutes, args.days, args.seed, args.start_price)
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    out = DATA_DIR / f"{args.symbol.upper()}_{args.interval_minutes}m_{args.days}d_SYNTHETIC.csv"
    out_df = df.copy()
    out_df["open_time"] = out_df["open_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out_df.to_csv(out, index=False)
    print(f"Wrote {out.relative_to(REPO_ROOT)}  ({out.stat().st_size / 1024:.1f} KiB, {len(df)} rows)")


if __name__ == "__main__":
    main()
