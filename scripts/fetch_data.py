"""CLI: fetch candles from Binance and write them to data/<SYMBOL>_<INTERVAL>_<DAYS>d.csv."""
from __future__ import annotations

import argparse
from pathlib import Path

from backend.data.binance_fetcher import BinanceFetcher, save_csv

REPO_ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = REPO_ROOT / "data"


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch Binance klines into data/ as CSV.")
    parser.add_argument("--symbol", default="BTCUSDT")
    parser.add_argument("--interval", default="1m")
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()

    fetcher = BinanceFetcher()
    print(f"Fetching {args.symbol} {args.interval} last {args.days}d from Binance...")
    df = fetcher.fetch_last_days(args.symbol, args.interval, args.days)
    print(f"  got {len(df)} candles  [{df['open_time'].min()}  ->  {df['open_time'].max()}]")

    out = DATA_DIR / f"{args.symbol.upper()}_{args.interval}_{args.days}d.csv"
    save_csv(df, out)
    print(f"Wrote {out.relative_to(REPO_ROOT)}  ({out.stat().st_size / 1024:.1f} KiB)")


if __name__ == "__main__":
    main()
