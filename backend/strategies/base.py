"""Base class for pluggable strategies."""
from __future__ import annotations

from abc import ABC, abstractmethod

import pandas as pd

from backend.engine.broker import Broker


class Strategy(ABC):
    """Strategies receive each bar and may submit/cancel orders via the broker."""

    @abstractmethod
    def on_start(self, broker: Broker, first_bar: pd.Series) -> None:
        """Called once before the first bar. Good place for initial limit orders."""

    @abstractmethod
    def on_bar(self, broker: Broker, bar: pd.Series) -> None:
        """Called on every bar after fills for that bar have been processed."""
