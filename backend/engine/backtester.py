"""Bar-driven backtest loop.

The Strategy receives each bar and interacts with the Broker via
`submit`/`cancel_all`. Orders submitted during bar T are eligible to fill on
bar T+1 (market) or any future bar whose range crosses the limit price.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol

import pandas as pd

from backend.engine.broker import Broker, Fill
from backend.engine.metrics import Metrics, compute_metrics


@dataclass
class EquityPoint:
    ts: str
    equity: float
    price: float
    position_qty: float


class StrategyProtocol(Protocol):
    def on_start(self, broker: Broker, first_bar: pd.Series) -> None: ...
    def on_bar(self, broker: Broker, bar: pd.Series) -> None: ...


@dataclass
class BacktestResult:
    metrics: Metrics
    equity_curve: list[EquityPoint]
    fills: list[Fill]
    # Series of closed-trade PnL (one entry per round-trip back-to-flat).
    closed_trades: list[float] = field(default_factory=list)
    params: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "metrics": self.metrics.to_dict(),
            "equity_curve": [
                {"ts": p.ts, "equity": round(p.equity, 4),
                 "price": round(p.price, 4), "position_qty": round(p.position_qty, 8)}
                for p in self.equity_curve
            ],
            "fills": [
                {"ts": f.ts, "side": f.side.value, "qty": round(f.quantity, 8),
                 "price": round(f.price, 4), "fee": round(f.fee, 6), "tag": f.tag}
                for f in self.fills
            ],
            "closed_trades": [round(t, 4) for t in self.closed_trades],
            "params": self.params,
        }


@dataclass
class Backtester:
    starting_cash: float = 10_000.0
    fee_rate: float = 0.001
    slippage_rate: float = 0.0002
    # Downsample equity curve for API transport: keep at most N points.
    equity_sample_cap: int = 2000

    def run(
        self,
        candles: pd.DataFrame,
        strategy: StrategyProtocol,
        params: dict | None = None,
    ) -> BacktestResult:
        if candles.empty:
            raise ValueError("No candles supplied to backtester.")

        broker = Broker(
            starting_cash=self.starting_cash,
            fee_rate=self.fee_rate,
            slippage_rate=self.slippage_rate,
        )
        equity: list[EquityPoint] = []
        closed_trades: list[float] = []
        in_position_mask: list[bool] = []

        # Track cost basis for realised-pnl accounting.
        cost_basis = 0.0
        realised_since_flat = 0.0
        was_in_position = False

        candles = candles.reset_index(drop=True)
        strategy.on_start(broker, candles.iloc[0])

        for i, row in candles.iterrows():
            ts = row["open_time"].isoformat() if hasattr(row["open_time"], "isoformat") else str(row["open_time"])
            # 1. Let pending orders try to fill against this bar.
            fills = broker.process_bar(ts, row["open"], row["high"], row["low"], row["close"])
            # 2. Track closed trades (position went from >0 back to 0).
            for f in fills:
                notional = f.quantity * f.price
                if f.side.value == "buy":
                    cost_basis += notional + f.fee
                else:
                    cost_basis -= notional - f.fee
                    # alternative: track realised per-fill; we use round-trip model below
            # Detect flat transition → realised PnL for this round-trip.
            now_in_position = broker.position_qty > 1e-12
            if was_in_position and not now_in_position:
                # Everything that entered / exited since last flat contributed to cash.
                # Use cost_basis: cash delta = -cost_basis
                trade_pnl = -cost_basis
                closed_trades.append(trade_pnl)
                cost_basis = 0.0
            was_in_position = now_in_position

            # 3. Give the strategy a chance to react to the new bar.
            strategy.on_bar(broker, row)

            # 4. Mark-to-market equity.
            eq = broker.equity(row["close"])
            equity.append(EquityPoint(ts=ts, equity=eq, price=row["close"],
                                      position_qty=broker.position_qty))
            in_position_mask.append(now_in_position)

        # If the backtest ended with open position, force-close at final close for metrics.
        if broker.position_qty > 1e-12:
            final_row = candles.iloc[-1]
            closing_notional = broker.position_qty * final_row["close"]
            closing_fee = closing_notional * broker.fee_rate
            cost_basis -= closing_notional - closing_fee
            closed_trades.append(-cost_basis)
            broker.cash += closing_notional - closing_fee
            broker.position_qty = 0.0
            # Adjust final equity point to reflect the synthetic close.
            equity[-1] = EquityPoint(
                ts=equity[-1].ts,
                equity=broker.cash,
                price=final_row["close"],
                position_qty=0.0,
            )

        equity_values = [p.equity for p in equity]
        metrics = compute_metrics(
            equity_curve=equity_values,
            starting_cash=self.starting_cash,
            closed_trades=closed_trades,
            in_position_mask=in_position_mask,
        )

        return BacktestResult(
            metrics=metrics,
            equity_curve=_downsample(equity, self.equity_sample_cap),
            fills=broker.fills,
            closed_trades=closed_trades,
            params=params or {},
        )


def _downsample(points: list[EquityPoint], cap: int) -> list[EquityPoint]:
    if len(points) <= cap:
        return points
    step = len(points) / cap
    out: list[EquityPoint] = []
    i = 0.0
    while int(i) < len(points):
        out.append(points[int(i)])
        i += step
    # Always keep the last bar so the equity reading lines up with reported PnL.
    if out[-1] is not points[-1]:
        out.append(points[-1])
    return out
