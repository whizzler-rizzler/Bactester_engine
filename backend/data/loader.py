"""Load committed CSV datasets into pandas DataFrames."""
from __future__ import annotations

from pathlib import Path

import pandas as pd

DATA_DIR = Path(__file__).resolve().parents[2] / "data"


def list_datasets(data_dir: Path | None = None) -> list[dict]:
    """Return metadata for every candle CSV in the data directory."""
    root = data_dir or DATA_DIR
    if not root.exists():
        return []
    out: list[dict] = []
    for p in sorted(root.glob("*.csv")):
        # Filename convention: SYMBOL_INTERVAL_DAYSd.csv  e.g. BTCUSDT_1m_30d.csv
        stem = p.stem
        parts = stem.split("_")
        symbol = parts[0] if parts else stem
        interval = parts[1] if len(parts) > 1 else "?"
        out.append({
            "name": stem,
            "path": str(p.relative_to(root.parent)),
            "symbol": symbol,
            "interval": interval,
            "size_bytes": p.stat().st_size,
        })
    return out


def load_candles(name: str, data_dir: Path | None = None) -> pd.DataFrame:
    """Load a dataset by filename stem (e.g. 'BTCUSDT_1m_30d')."""
    root = data_dir or DATA_DIR
    path = root / f"{name}.csv"
    if not path.exists():
        raise FileNotFoundError(f"Dataset not found: {path}")
    df = pd.read_csv(path, parse_dates=["open_time"])
    if df["open_time"].dt.tz is None:
        df["open_time"] = df["open_time"].dt.tz_localize("UTC")
    return df
