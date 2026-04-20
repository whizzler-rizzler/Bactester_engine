"""FastAPI routes: strategy catalogue, datasets, and backtest runner."""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field

from backend.data.loader import list_datasets, load_candles
from backend.engine.backtester import Backtester
from backend.strategies import build_strategy, list_strategies

router = APIRouter()


@router.get("/strategies")
def get_strategies() -> list[dict]:
    """Return available strategies with their JSON-schema so the UI can render forms."""
    return list_strategies()


@router.get("/datasets")
def get_datasets() -> list[dict]:
    return list_datasets()


class BacktestRequest(BaseModel):
    strategy: str = Field(..., description="Strategy name, e.g. 'ladder_bot'.")
    params: dict[str, Any] = Field(default_factory=dict)
    dataset: str = Field(..., description="Dataset filename stem, e.g. 'BTCUSDT_1m_30d'.")
    starting_cash: float = Field(10_000.0, gt=0.0)
    fee_rate: float = Field(0.001, ge=0.0, le=0.05)
    slippage_rate: float = Field(0.0002, ge=0.0, le=0.05)
    limit_bars: int | None = Field(
        None, ge=100,
        description="Optional cap on bars (useful for faster UI runs).",
    )


@router.post("/backtest")
def run_backtest(req: BacktestRequest) -> dict:
    try:
        strategy, params_used = build_strategy(req.strategy, req.params)
    except KeyError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid params: {e}") from e

    try:
        candles = load_candles(req.dataset)
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e)) from e

    if req.limit_bars:
        candles = candles.head(req.limit_bars)

    engine = Backtester(
        starting_cash=req.starting_cash,
        fee_rate=req.fee_rate,
        slippage_rate=req.slippage_rate,
    )
    result = engine.run(candles, strategy, params={"strategy": req.strategy, **params_used})
    return {
        "strategy": req.strategy,
        "dataset": req.dataset,
        "bars": int(len(candles)),
        **result.to_dict(),
    }
