"""strategy.py"""
from abc import ABC, abstractmethod
from hqg_algorithms.types import BacktestWindow, Cadence, Slice, PortfolioView

class Strategy(ABC):
    """
    Base interface for all trading strategies.

    Each subclass defines:
      - The asset universe it trades.
            - The backtest window (mandatory start/end dates).
      - The cadence (how often it's called and when trades execute).
      - The trading logic that converts data into target portfolio weights.

    The backtester calls:
      1. strategy.universe() to know what tickers to load.
    2. strategy.backtest_window() to set the start/end date range.
    3. strategy.cadence() to schedule on_data calls.
    4. strategy.on_data(t, slice_) each time new data arrives.
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
    def backtest_window(self) -> BacktestWindow:
        """
        Return a BacktestWindow with mandatory start and end dates.

        Example:
            return BacktestWindow(date(2010, 1, 1), date(2024, 12, 31))

        Used by the backtester to constrain the historical data window.
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
    def on_data(self, data: Slice, portfolio: PortfolioView) -> dict[str, float] | None:
        """
        Main signal logic.

        Args:
            data: a "slice" of the current bar's data, typically a dict:
                  { "SPY": {"open":..., "high":..., "low":..., "close":...}, ... }

        Returns:
            dict[str, float]: target portfolio weights, e.g. {"SPY": 0.6, "IEF": 0.4}
            or None to indicate no change to previous allocation

        - The returned dictionary expresses the complete target allocation.
        - If a symbol is omitted, we sell it down to zero.
        - Sum of weights less than 1 implies remaining balance held as cash.
        - {} means we should covert our portfolio to fully cash.
        - None means skip rebalance (no signal update this bar).

        Called automatically according to cadence().
        """
