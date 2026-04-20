"""Ladder Bot strategy.

Modelled after the DCA-ladder pattern described by tools like Sigma Engine /
Bitsgap / Pionex "DCA bot with laddered entries":

  * The bot defines a *ladder* of N buy rungs below a reference price.
  * Spacing between rungs can be arithmetic ("arithmetic", equal % apart)
    or geometric ("geometric", each rung `step_multiplier` further than the
    previous one). Geometric spacing lets later rungs sit much deeper.
  * Each rung has its own quote-size; `size_multiplier` scales size per step
    (e.g. 1.5 = later rungs buy progressively more — safety-order pattern).
  * Once any rung fills, a pooled take-profit sell is placed at
    `avg_entry * (1 + take_profit_pct)` for the whole accumulated position.
    When TP fires the ladder resets and re-arms from the current price.
  * An optional global stop-loss closes the position if price drops below
    `avg_entry * (1 - stop_loss_pct)`.
  * `max_active_rungs` caps how many rungs can be open concurrently.

Every parameter is exposed in the UI panel via the pydantic schema below.
"""
from __future__ import annotations

from enum import Enum

import pandas as pd
from pydantic import BaseModel, Field, field_validator

from backend.engine.broker import Broker, Order, OrderSide, OrderType
from backend.strategies.base import Strategy

NAME = "ladder_bot"
DESCRIPTION = (
    "DCA-style laddered buy rungs below a reference price, with pooled "
    "take-profit and optional global stop-loss. Supports arithmetic or "
    "geometric rung spacing and progressive sizing."
)


class RungSpacing(str, Enum):
    arithmetic = "arithmetic"
    geometric = "geometric"


class Direction(str, Enum):
    long = "long"  # only long laddering supported for now


class LadderBotParams(BaseModel):
    """UI-exposed parameters. Percentages are expressed as percent, not fraction."""

    direction: Direction = Field(Direction.long, description="Ladder direction (long only).")

    num_rungs: int = Field(
        5, ge=1, le=30,
        description="How many laddered buy orders to place below the reference price.",
    )
    first_rung_offset_pct: float = Field(
        0.5, ge=0.0, le=50.0,
        description="Distance of the first (highest) rung below the reference price, in %.",
    )
    rung_step_pct: float = Field(
        0.5, ge=0.01, le=20.0,
        description="Spacing between rungs, in %. (Base step; see step_multiplier.)",
    )
    step_multiplier: float = Field(
        1.0, ge=0.5, le=5.0,
        description="Geometric step multiplier. 1.0 = arithmetic spacing; 1.5 = each "
                    "rung is 1.5× farther than the previous.",
    )
    spacing: RungSpacing = Field(
        RungSpacing.geometric,
        description="arithmetic: equal step. geometric: step grows by step_multiplier.",
    )

    base_order_quote: float = Field(
        500.0, gt=0.0,
        description="Quote-currency size of the FIRST rung (e.g. 500 USDT).",
    )
    size_multiplier: float = Field(
        1.3, ge=0.5, le=5.0,
        description="Each subsequent rung's size = previous × size_multiplier. "
                    "1.0 = flat sizing; >1 = martingale-style growing safety orders.",
    )

    take_profit_pct: float = Field(
        1.0, ge=0.05, le=50.0,
        description="Pooled take-profit above weighted average entry, in %.",
    )
    stop_loss_pct: float | None = Field(
        None, ge=0.5, le=90.0,
        description="Optional stop-loss below average entry, in %. Empty = no stop.",
    )

    max_active_rungs: int | None = Field(
        None, ge=1, le=30,
        description="Cap on simultaneously-open rungs (defaults to num_rungs).",
    )
    cooldown_bars: int = Field(
        0, ge=0, le=10_000,
        description="Bars to wait after TP/SL before re-arming the ladder.",
    )

    @field_validator("max_active_rungs")
    @classmethod
    def _cap(cls, v: int | None, info) -> int | None:
        if v is not None and v > info.data.get("num_rungs", v):
            return info.data.get("num_rungs")
        return v


def build(params: LadderBotParams) -> "LadderBot":
    return LadderBot(params)


class LadderBot(Strategy):
    def __init__(self, params: LadderBotParams):
        self.p = params
        self._armed = False
        self._ref_price: float | None = None
        self._tp_order_id: int | None = None
        self._sl_order_id: int | None = None
        self._cooldown_left = 0
        self._prev_in_position = False
        self._rung_sizes_base: list[float] = self._compute_rung_base_sizes()

    # ------------------------------------------------------------------
    def _compute_rung_base_sizes(self) -> list[float]:
        sizes: list[float] = []
        cur = self.p.base_order_quote
        for _ in range(self.p.num_rungs):
            sizes.append(cur)
            cur *= self.p.size_multiplier
        return sizes

    def _rung_offsets_pct(self) -> list[float]:
        """Cumulative %-offsets below reference, one per rung."""
        offsets: list[float] = []
        offset = self.p.first_rung_offset_pct
        step = self.p.rung_step_pct
        for _ in range(self.p.num_rungs):
            offsets.append(offset)
            if self.p.spacing is RungSpacing.geometric:
                step = step * self.p.step_multiplier
            offset += step
        return offsets

    def _cap_rungs(self) -> int:
        return self.p.max_active_rungs or self.p.num_rungs

    # ------------------------------------------------------------------
    def on_start(self, broker: Broker, first_bar: pd.Series) -> None:
        self._arm_ladder(broker, ref_price=float(first_bar["open"]))

    def on_bar(self, broker: Broker, bar: pd.Series) -> None:
        in_position = broker.position_qty > 1e-12
        just_exited = self._prev_in_position and not in_position
        self._prev_in_position = in_position

        if just_exited:
            self._reset_after_exit(broker)

        if self._cooldown_left > 0:
            self._cooldown_left -= 1
            if self._cooldown_left == 0 and not self._armed and not in_position:
                self._arm_ladder(broker, ref_price=float(bar["close"]))
            return

        if in_position:
            self._sync_exits(broker)
        elif not self._armed:
            self._arm_ladder(broker, ref_price=float(bar["close"]))

    # ------------------------------------------------------------------
    def _arm_ladder(self, broker: Broker, ref_price: float) -> None:
        self._ref_price = ref_price
        broker.cancel_all(tag_prefix="ladder_rung")
        offsets = self._rung_offsets_pct()
        cap = self._cap_rungs()
        for i, offset in enumerate(offsets[:cap]):
            rung_price = ref_price * (1.0 - offset / 100.0)
            if rung_price <= 0:
                continue
            qty = self._rung_sizes_base[i] / rung_price
            broker.submit(Order(
                side=OrderSide.BUY,
                type=OrderType.LIMIT,
                quantity=qty,
                price=rung_price,
                tag=f"ladder_rung_{i}",
            ))
        self._armed = True
        self._tp_order_id = None
        self._sl_order_id = None

    def _sync_exits(self, broker: Broker) -> None:
        """Keep TP (and SL) orders aligned with the current avg-entry."""
        avg = broker.avg_entry_price
        if avg <= 0:
            return
        tp_price = avg * (1.0 + self.p.take_profit_pct / 100.0)
        # Replace TP order if price moved (avg changed after new rung fill).
        broker.cancel_all(tag_prefix="ladder_tp")
        self._tp_order_id = broker.submit(Order(
            side=OrderSide.SELL,
            type=OrderType.LIMIT,
            quantity=broker.position_qty,
            price=tp_price,
            tag="ladder_tp",
        ))

        if self.p.stop_loss_pct is not None:
            sl_price = avg * (1.0 - self.p.stop_loss_pct / 100.0)
            broker.cancel_all(tag_prefix="ladder_sl")
            self._sl_order_id = broker.submit(Order(
                side=OrderSide.SELL,
                type=OrderType.STOP,
                quantity=broker.position_qty,
                price=sl_price,
                tag="ladder_sl",
            ))

    def _reset_after_exit(self, broker: Broker) -> None:
        broker.cancel_all(tag_prefix="ladder_")
        self._armed = False
        self._tp_order_id = None
        self._sl_order_id = None
        if self.p.cooldown_bars > 0:
            self._cooldown_left = self.p.cooldown_bars
        # If no cooldown, re-arm immediately on next bar (use its close as ref).
