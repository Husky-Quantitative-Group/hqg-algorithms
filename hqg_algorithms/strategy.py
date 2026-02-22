"""strategy.py"""
from abc import ABC, abstractmethod
from hqg_algorithms.types import Cadence, Slice, PortfolioView, Signal

class Strategy(ABC):
    """
    Base interface for all trading strategies.

    Each subclass defines:
      - The asset universe it trades.
      - The cadence (how often it's called and when trades execute).
      - The trading logic that converts data into a Signal.

    The backtester calls:
      1. strategy.universe() to know what tickers to load.
      2. strategy.cadence() to schedule on_data calls.
      3. strategy.on_data(data, portfolio) each time new data arrives.
    """

    def __init__(self) -> None:
        """Initialize internal state for the strategy (if any)."""

    @abstractmethod
    def universe(self) -> list[str]:
        """
        Return a list of tickers or instruments this strategy trades.

        Example:
            return ["SPY", "IEF", "GLD"]

        Used by the backtester to determine what data to load.
        """

    @abstractmethod
    def cadence(self) -> Cadence:
        """
        Return a Cadence object describing:
          - bar_size (e.g., daily, weekly)
          - execution (when on_data fires and when trades fill, e.g.
            CLOSE_TO_NEXT_OPEN, CLOSE_TO_CLOSE, or OPEN_TO_OPEN)

        This tells the executor when to call on_data and when to fill orders.
        """

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

        Called automatically according to cadence().
        """