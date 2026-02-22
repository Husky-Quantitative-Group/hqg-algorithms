"""strategy.py"""
from abc import ABC, abstractmethod
from hqg_algorithms.types import Cadence, Slice, PortfolioView

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
          - bar_size (e.g., 1 day, 1 week)
          - call_phase ("on_bar_close" or "on_bar_open")
          - exec_lag_bars (how many bars later to execute trades)

        This tells the executor when to call on_data and when to fill orders.
        """

    @abstractmethod
    def on_data(self, data: Slice, portfolio: PortfolioView) -> dict[str, float] | None:
        """
        Main signal logic.

        Args:
            data: a Slice mapping each symbol to a Bar dataclass with typed OHLCV fields. 
                Access prices via helpers like data.close("SPY") or grab the full bar with
                data.bar("SPY") for direct attribute access (e.g. bar.open, bar.high, ...).
            portfolio: a read-only PortfolioView with current equity, cash, positions,
                and weights.

        Returns:
            dict[str, float]: target portfolio weights, e.g. {"SPY": 0.6, "IEF": 0.4}
            or None to indicate no change to previous allocation.

        - The returned dictionary expresses the complete target allocation.
        - If a symbol is omitted, we sell it down to zero.
        - Sum of weights less than 1 implies remaining balance held as cash.
        - {} means we should convert our portfolio to fully cash.
        - None means skip rebalance (no signal update this bar).

        Called automatically according to cadence().
        """