"""In-memory broker that simulates order fills against OHLC bars.

Design notes:
* The engine is bar-driven. At each bar we get open/high/low/close.
* Market orders fill at the NEXT bar open (no look-ahead).
* Limit orders fill inside a bar if [low, high] contains the limit price.
* Fees are deducted from cash on every fill. Slippage is a fraction of price
  applied in the adverse direction.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class OrderSide(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"       # Trigger-then-market: fills at trigger when price crosses it.


@dataclass
class Order:
    side: OrderSide
    type: OrderType
    quantity: float
    price: float | None = None  # required for LIMIT
    tag: str = ""               # e.g. "ladder_step_3" or "ladder_tp"
    id: int = 0                 # assigned by broker


@dataclass
class Fill:
    order_id: int
    ts: str                     # ISO timestamp
    side: OrderSide
    quantity: float
    price: float
    fee: float
    tag: str


@dataclass
class Broker:
    starting_cash: float
    fee_rate: float = 0.001         # 10 bps per fill (taker on Binance spot by default)
    slippage_rate: float = 0.0002   # 2 bps market-order slippage
    cash: float = 0.0
    position_qty: float = 0.0
    avg_entry_price: float = 0.0
    _next_order_id: int = 1
    _open_orders: list[Order] = field(default_factory=list)
    fills: list[Fill] = field(default_factory=list)

    def __post_init__(self) -> None:
        self.cash = self.starting_cash

    # ------------------------------------------------------------------
    # Order management
    # ------------------------------------------------------------------
    def submit(self, order: Order) -> int:
        order.id = self._next_order_id
        self._next_order_id += 1
        self._open_orders.append(order)
        return order.id

    def cancel(self, order_id: int) -> bool:
        for i, o in enumerate(self._open_orders):
            if o.id == order_id:
                self._open_orders.pop(i)
                return True
        return False

    def cancel_all(self, tag_prefix: str | None = None) -> int:
        if tag_prefix is None:
            n = len(self._open_orders)
            self._open_orders.clear()
            return n
        kept = [o for o in self._open_orders if not o.tag.startswith(tag_prefix)]
        removed = len(self._open_orders) - len(kept)
        self._open_orders = kept
        return removed

    @property
    def open_orders(self) -> list[Order]:
        return list(self._open_orders)

    # ------------------------------------------------------------------
    # Bar processing
    # ------------------------------------------------------------------
    def process_bar(self, ts: str, o: float, h: float, l: float, c: float) -> list[Fill]:
        """Match all open orders against this bar. Returns fills produced."""
        new_fills: list[Fill] = []
        remaining: list[Order] = []
        for order in self._open_orders:
            fill = self._try_fill(order, ts, o, h, l)
            if fill is None:
                remaining.append(order)
            else:
                new_fills.append(fill)
        self._open_orders = remaining
        self.fills.extend(new_fills)
        return new_fills

    def _try_fill(self, order: Order, ts: str, o: float, h: float, l: float) -> Fill | None:
        if order.type is OrderType.MARKET:
            # Market fills at bar open, adjusted by slippage.
            if order.side is OrderSide.BUY:
                price = o * (1 + self.slippage_rate)
            else:
                price = o * (1 - self.slippage_rate)
            return self._execute(order, ts, price)

        assert order.price is not None
        if order.type is OrderType.LIMIT:
            # Maker-style: buy fills when price dips to/through; sell when it rises to/through.
            if order.side is OrderSide.BUY and l <= order.price:
                return self._execute(order, ts, order.price)
            if order.side is OrderSide.SELL and h >= order.price:
                return self._execute(order, ts, order.price)
            return None

        if order.type is OrderType.STOP:
            # Trigger-direction is opposite of LIMIT: a SELL stop fires when low
            # crosses DOWN through trigger; a BUY stop fires when high crosses UP.
            # We fill at the trigger price, then apply slippage in adverse direction.
            if order.side is OrderSide.SELL and l <= order.price:
                fill_price = order.price * (1 - self.slippage_rate)
                return self._execute(order, ts, fill_price)
            if order.side is OrderSide.BUY and h >= order.price:
                fill_price = order.price * (1 + self.slippage_rate)
                return self._execute(order, ts, fill_price)
            return None

        return None

    def _execute(self, order: Order, ts: str, price: float) -> Fill:
        notional = order.quantity * price
        fee = notional * self.fee_rate
        if order.side is OrderSide.BUY:
            # Update weighted-average entry price over the net long position.
            new_qty = self.position_qty + order.quantity
            if new_qty > 0 and self.position_qty >= 0:
                self.avg_entry_price = (
                    (self.avg_entry_price * self.position_qty) + (price * order.quantity)
                ) / new_qty
            self.position_qty = new_qty
            self.cash -= notional + fee
        else:
            # Sell: reduces position. If flat, avg price is reset.
            self.position_qty -= order.quantity
            self.cash += notional - fee
            if abs(self.position_qty) < 1e-12:
                self.position_qty = 0.0
                self.avg_entry_price = 0.0
        return Fill(
            order_id=order.id,
            ts=ts,
            side=order.side,
            quantity=order.quantity,
            price=price,
            fee=fee,
            tag=order.tag,
        )

    # ------------------------------------------------------------------
    # Valuation
    # ------------------------------------------------------------------
    def equity(self, mark_price: float) -> float:
        return self.cash + self.position_qty * mark_price
