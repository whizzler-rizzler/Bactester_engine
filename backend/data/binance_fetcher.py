"""Binance public REST client for historical klines.

Uses the `/api/v3/klines` endpoint. No auth required. Paginates via the
`startTime` cursor, since Binance caps each response at 1000 candles.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Literal

import httpx
import pandas as pd

Interval = Literal["1m", "3m", "5m", "15m", "30m", "1h", "4h", "1d"]

_INTERVAL_MS: dict[str, int] = {
    "1m": 60_000,
    "3m": 180_000,
    "5m": 300_000,
    "15m": 900_000,
    "30m": 1_800_000,
    "1h": 3_600_000,
    "4h": 14_400_000,
    "1d": 86_400_000,
}

# Binance klines response columns (12). We keep the first 6 + quote volume.
_KLINE_COLUMNS = [
    "open_time", "open", "high", "low", "close", "volume",
    "close_time", "quote_volume", "trades",
    "taker_buy_base", "taker_buy_quote", "ignore",
]


@dataclass
class BinanceFetcher:
    base_url: str = "https://api.binance.com"
    limit: int = 1000  # max per request
    timeout: float = 15.0
    # Simple courtesy throttle between paginated calls (Binance allows 1200/min)
    sleep_between_calls: float = 0.15

    def fetch_klines(
        self,
        symbol: str,
        interval: Interval,
        start_ms: int,
        end_ms: int,
    ) -> pd.DataFrame:
        """Fetch all klines in [start_ms, end_ms). Paginates as needed."""
        step = _INTERVAL_MS[interval]
        all_rows: list[list] = []
        cursor = start_ms

        with httpx.Client(base_url=self.base_url, timeout=self.timeout) as client:
            while cursor < end_ms:
                params = {
                    "symbol": symbol.upper(),
                    "interval": interval,
                    "startTime": cursor,
                    "endTime": end_ms,
                    "limit": self.limit,
                }
                resp = client.get("/api/v3/klines", params=params)
                resp.raise_for_status()
                batch = resp.json()
                if not batch:
                    break
                all_rows.extend(batch)
                last_open = batch[-1][0]
                next_cursor = last_open + step
                if next_cursor <= cursor:
                    # Defensive: API returned stale data; stop to avoid infinite loop.
                    break
                cursor = next_cursor
                if len(batch) < self.limit:
                    # We've drained the available history for this window.
                    break
                time.sleep(self.sleep_between_calls)

        if not all_rows:
            return _empty_frame()

        df = pd.DataFrame(all_rows, columns=_KLINE_COLUMNS)
        return _normalise(df)

    def fetch_last_days(
        self,
        symbol: str,
        interval: Interval,
        days: int,
        end: datetime | None = None,
    ) -> pd.DataFrame:
        end_dt = end or datetime.now(tz=timezone.utc)
        end_ms = int(end_dt.timestamp() * 1000)
        start_ms = end_ms - days * 86_400_000
        return self.fetch_klines(symbol, interval, start_ms, end_ms)


def _normalise(df: pd.DataFrame) -> pd.DataFrame:
    df = df[["open_time", "open", "high", "low", "close", "volume", "quote_volume", "trades"]].copy()
    df["open_time"] = pd.to_datetime(df["open_time"], unit="ms", utc=True)
    numeric_cols = ["open", "high", "low", "close", "volume", "quote_volume"]
    df[numeric_cols] = df[numeric_cols].astype(float)
    df["trades"] = df["trades"].astype(int)
    df = df.drop_duplicates(subset="open_time").sort_values("open_time").reset_index(drop=True)
    return df


def _empty_frame() -> pd.DataFrame:
    cols = ["open_time", "open", "high", "low", "close", "volume", "quote_volume", "trades"]
    return pd.DataFrame(columns=cols)


def save_csv(df: pd.DataFrame, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    # ISO8601 timestamps so the file is human-diffable in git.
    out = df.copy()
    out["open_time"] = out["open_time"].dt.strftime("%Y-%m-%dT%H:%M:%SZ")
    out.to_csv(path, index=False)
