"""strategy.py"""
from abc import ABC, abstractmethod
from typing import Callable
from hqg_algorithms.types import Cadence, Slice, PortfolioView, Signal

class Strategy(ABC):
    """
    Base interface for all trading strategies.

    Each subclass defines:
      - The asset universe it trades (class variable).
      - The cadence: how often it's called and when trades execute (class variable).
      - The trading logic that converts data into a Signal (on_data method).

    Usage:
        from hqg_algorithms import Strategy, Cadence, BarSize, ExecutionTiming

        class MyStrategy(Strategy):
            universe = ["SPY", "IEF", "GLD"]
            cadence = Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

            def on_data(self, data, portfolio):
                ...

    Notes:
        - universe must be a list literal of ticker strings.
        - cadence must be a direct Cadence(...) call with BarSize.X and/or
          ExecutionTiming.Y keyword arguments. Defaults to daily bars with
          close-to-close execution if omitted.
        - These are parsed via AST (not executed) on the host for data loading,
          so these definitions cannot use variables, function calls, or aliased imports.
    """

    universe: list[str]
    """List of tickers this strategy trades. e.g. ["SPY", "IEF", "GLD"]"""

    cadence: Cadence = Cadence()
    """How often on_data is called and when trades fill. Defaults to daily, close-to-close."""

    _log_handler: Callable[[str], None] = staticmethod(print)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        if not hasattr(cls, 'universe') or not isinstance(cls.universe, list) or len(cls.universe) == 0:
            raise TypeError(
                f"{cls.__name__} must define 'universe' as a non-empty list of tickers. "
                f'e.g. universe = ["SPY", "IEF"]'
            )
    

    def log(self, message: str) -> None:
        self._log_handler(message)


    @abstractmethod
    def on_data(self, data: Slice, portfolio: PortfolioView) -> Signal:
        """
        Main signal logic.

        Args:
            data: a Slice mapping each symbol to a Bar dataclass with typed OHLCV fields.
                Access prices via helpers like data.close("SPY") or grab the full bar with
                data.bar("SPY") for direct attribute access (e.g. bar.open, bar.high, ...).
            portfolio: a read-only PortfolioView with current equity, cash, positions,
                and weights.

        Returns one of:
            TargetWeights({"SPY": 0.6, "IEF": 0.4})
                - Set the portfolio to these target weights.
                - Omitted symbols are sold to zero.
                - Weights summing to less than 1.0 leave the remainder in cash.
                - ValueError: If any weight is negative or weights sum above 1.0.
            Hold()
                Keep the current allocation unchanged (skip this bar).
            Liquidate()
                Sell everything and move fully to cash.

        Called automatically according to cadence.
        """