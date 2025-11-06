"""strategy.py"""
from abc import ABC, abstractmethod
from hqg_algorithms.types import Cadence, Slice

class Strategy(ABC):
    """
    Base interface for all trading strategies.

    Each subclass defines:
      - The asset universe it trades.
      - The cadence (how often it's called and when trades execute).
      - The trading logic that converts data into target portfolio weights.

    The backtester calls:
      1. strategy.universe() to know what tickers to load.
      2. strategy.cadence() to schedule on_data calls.
      3. strategy.on_data(t, slice_) each time new data arrives.
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
        Return a Cadence object or similar structure describing:
          - bar_size (e.g., 1 day, 5 minutes)
          - call_phase ("on_bar_close" or "on_bar_open")
          - exec_lag_bars (how many bars later to execute trades)

        This tells the executor when to call on_data and when to fill orders.
        """

    @abstractmethod
    def on_data(self, data: Slice) -> dict[str, float] | None:
        """
        Main signal logic.

        Args:
            data: a "slice" of the current bar's data, typically a dict:
                  { "SPY": {"open":..., "high":..., "low":..., "close":...}, ... }

        Returns:
            dict[str, float]: target portfolio weights, e.g. {"SPY": 0.6, "IEF": 0.4}
            or None to indicate no change / hold current allocation.

        Called automatically according to cadence().
        """