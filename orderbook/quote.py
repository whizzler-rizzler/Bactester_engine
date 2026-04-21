"""Canonical L1 quote record used throughout the module.

`@bookTicker` from Binance delivers: best bid price, best bid qty, best ask
price, best ask qty, per update. A tick is the smallest reasoning unit here;
there is no OHLC bar concept.
"""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(slots=True, frozen=True)
class Quote:
    ts_ms: int          # epoch millis
    bid_price: float
    bid_qty: float
    ask_price: float
    ask_qty: float

    @property
    def mid(self) -> float:
        return 0.5 * (self.bid_price + self.ask_price)

    @property
    def spread(self) -> float:
        return self.ask_price - self.bid_price

    @property
    def imbalance(self) -> float:
        """bid_qty / (bid_qty + ask_qty). 0.5 = neutral, >0.5 = bid-heavy."""
        total = self.bid_qty + self.ask_qty
        return self.bid_qty / total if total > 0 else 0.5
