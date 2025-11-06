# types.py
from dataclasses import dataclass
from datetime import timedelta
from typing import Optional

@dataclass(frozen=True)
class Cadence:
    """Defines how often a strategy runs and when trades execute."""
    bar_size: timedelta = timedelta(days=1)
    call_phase: str = "on_bar_close"   # or "on_bar_open"
    exec_lag_bars: int = 1             # bars between signal and execution


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

    def close(self, symbol: str) -> Optional[float]:
        """Return the close price for a symbol, or None if missing."""
        return self.get(symbol, {}).get("close")