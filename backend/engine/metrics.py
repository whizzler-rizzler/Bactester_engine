"""Performance metrics for a completed backtest."""
from __future__ import annotations

import math
from dataclasses import dataclass


@dataclass
class Metrics:
    total_return_pct: float
    pnl: float
    max_drawdown_pct: float
    sharpe: float
    num_trades: int
    win_rate_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    exposure_pct: float

    def to_dict(self) -> dict:
        return {k: (None if isinstance(v, float) and math.isnan(v) else v)
                for k, v in self.__dict__.items()}


def compute_metrics(
    equity_curve: list[float],
    starting_cash: float,
    closed_trades: list[float],      # realised PnL per closed trade cycle
    in_position_mask: list[bool],    # len == equity_curve
    bars_per_year: float = 365 * 24 * 60,   # 1-minute bars
) -> Metrics:
    if not equity_curve:
        return Metrics(0, 0, 0, 0, 0, 0, 0, 0, 0, 0)

    final = equity_curve[-1]
    pnl = final - starting_cash
    total_return = pnl / starting_cash * 100.0

    # Max drawdown on equity curve.
    peak = equity_curve[0]
    max_dd = 0.0
    for v in equity_curve:
        if v > peak:
            peak = v
        dd = (v - peak) / peak if peak > 0 else 0.0
        if dd < max_dd:
            max_dd = dd
    max_dd_pct = max_dd * 100.0

    # Sharpe from bar-to-bar returns, annualised for 1m bars.
    returns: list[float] = []
    for i in range(1, len(equity_curve)):
        prev = equity_curve[i - 1]
        if prev > 0:
            returns.append((equity_curve[i] - prev) / prev)
    if len(returns) > 1:
        mean = sum(returns) / len(returns)
        var = sum((r - mean) ** 2 for r in returns) / (len(returns) - 1)
        std = var ** 0.5
        sharpe = (mean / std) * (bars_per_year ** 0.5) if std > 0 else 0.0
    else:
        sharpe = 0.0

    num_trades = len(closed_trades)
    wins = [t for t in closed_trades if t > 0]
    losses = [t for t in closed_trades if t < 0]
    win_rate = (len(wins) / num_trades * 100.0) if num_trades else 0.0
    avg_win = (sum(wins) / len(wins)) if wins else 0.0
    avg_loss = (sum(losses) / len(losses)) if losses else 0.0
    total_wins = sum(wins)
    total_losses = -sum(losses)
    profit_factor = (total_wins / total_losses) if total_losses > 0 else (
        float("inf") if total_wins > 0 else 0.0
    )

    exposure = (sum(1 for x in in_position_mask if x) / len(in_position_mask) * 100.0
                if in_position_mask else 0.0)

    return Metrics(
        total_return_pct=round(total_return, 4),
        pnl=round(pnl, 2),
        max_drawdown_pct=round(max_dd_pct, 4),
        sharpe=round(sharpe, 4),
        num_trades=num_trades,
        win_rate_pct=round(win_rate, 2),
        avg_win=round(avg_win, 2),
        avg_loss=round(avg_loss, 2),
        profit_factor=round(profit_factor, 4) if profit_factor != float("inf") else None,
        exposure_pct=round(exposure, 2),
    )
