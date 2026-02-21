"""types.py"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class BarSize(str, Enum):
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1m"
    QUARTERLY = "1q"

class CallPhase(str, Enum):
    ON_BAR_CLOSE = "on_bar_close"
    ON_BAR_OPEN = "on_bar_open"


@dataclass(frozen=True)
class Cadence:
    """Defines how often a strategy runs and when trades execute."""
    bar_size: BarSize = BarSize.DAILY              # bar resolution (1d, 1w, 1m, 1q)
    call_phase: CallPhase = CallPhase.ON_BAR_CLOSE # when on_data fires within each bar
    exec_lag_bars: int = 0                         # bars between signal and execution


class Slice(dict[str, dict[str, float]]):
    """
    Snapshot of OHLCV data for all symbols at one timestep.

    Structure:
        {
            "SPY": {"open": 444.2, "high": 445.0, "low": 443.9,
                    "close": 444.5, "volume": 1.2e7},
            "IEF": {"open": 97.1,  "high": 97.5,  "low": 97.0,
                    "close": 97.4,  "volume": 4.1e6},
        }
    """

    def symbols(self) -> list[str]:
        """Return list of all symbols in this slice."""
        return list(self.keys())

    def has(self, symbol: str) -> bool:
        """Check whether this slice includes a given symbol."""
        return symbol in self

    def _get_field(self, symbol: str, field: str) -> Optional[float]:
        """Return a specific OHLCV field for a symbol, or None if missing."""
        return self.get(symbol, {}).get(field)

    def open(self, symbol: str) -> Optional[float]:
        """Return the open price for a symbol, or None if missing."""
        return self._get_field(symbol, "open")

    def high(self, symbol: str) -> Optional[float]:
        """Return the high price for a symbol, or None if missing."""
        return self._get_field(symbol, "high")

    def low(self, symbol: str) -> Optional[float]:
        """Return the low price for a symbol, or None if missing."""
        return self._get_field(symbol, "low")

    def close(self, symbol: str) -> Optional[float]:
        """Return the close price for a symbol, or None if missing."""
        return self._get_field(symbol, "close")

    def volume(self, symbol: str) -> Optional[float]:
        """Return the volume for a symbol, or None if missing."""
        return self._get_field(symbol, "volume")
@dataclass(frozen=True)
class PortfolioView:
    """Read-only snapshot of the strategy's current portfolio state."""
    equity: float                 # total value of the strategy's portfolio
    cash: float                   # available, unallocated cash
    positions: dict[str, float]   # quantity of each symbol
    weights: dict[str, float]     # current portfolio weights (by value)
