"""types.py"""
from __future__ import annotations
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from types import MappingProxyType
from typing import Mapping, Optional

AltSeries = Mapping[datetime, float]
AltHistory = Mapping[str, AltSeries]


class BarSize(str, Enum):
    DAILY = "1d"
    WEEKLY = "1w"
    MONTHLY = "1m"
    QUARTERLY = "1q"

class ExecutionTiming(str, Enum):
    CLOSE_TO_CLOSE = "close_to_close"           # DEFAULT: signal on close, fill same close
    CLOSE_TO_NEXT_OPEN = "close_to_next_open"   # signal on close, fill next open


@dataclass(frozen=True)
class Cadence:
    """Defines how often a strategy runs and when trades execute."""
    bar_size: BarSize = BarSize.DAILY                               # bar resolution (1d, 1w, 1m, 1q)
    execution: ExecutionTiming = ExecutionTiming.CLOSE_TO_CLOSE     # signal on close, fill same close


@dataclass(frozen=True)
class Bar:
    """OHLCV data for a single symbol at one timestep."""
    open: float
    high: float
    low: float
    close: float
    volume: Optional[float]     # not available for all data


class Slice(Mapping[str, Bar]):
    """
    Frozen, point-in-time snapshot of data for one timestep.

    OHLCV bars are the market data for this timestep.

    Alternative data exposed through alt_series()/alt_value() must already
    be point-in-time correct for this Slice's timestamp. Slice performs no
    available_at filtering itself and cannot detect a violation; the caller
    constructing each Slice is responsible for enforcing that no future
    revisions are included. Each key is the OBSERVATION period the value describes (e.g. the start
    of a fiscal quarter for GDP), not the date the value became known.

    Structure:
        {
            "SPY": Bar(open=444.2, high=445.0, low=443.9, close=444.5, volume=1.2e7),
            "IEF": Bar(open=97.1,  high=97.5,  low=97.0, close=97.4,  volume=4.1e6),
        }

    Alt data (per series, via alt_series(series_id)):
        {
            datetime(2023, 1, 1): 17149.6,    # Q1 2023 GDP, latest known value
            datetime(2023, 4, 1): 17299.9,    # Q2 2023 GDP, latest known value
            ...
        }
    """

    def __init__(self, data: dict[str, Bar], alt_history: Optional[AltHistory] = None):
        self._data = dict(data)
        # Per-series alt histories are expected to be immutable cached views
        # from AltDataState. Preserve their object identity so unchanged
        # series do not get copied on every Slice construction.
        self._alt_history = MappingProxyType(dict(alt_history or {}))

    def __getitem__(self, key: str) -> Bar:
        return self._data[key]

    def __len__(self) -> int:
        return len(self._data)

    def __iter__(self):
        return iter(self._data)

    def __repr__(self) -> str:
        return f"Slice({self._data!r})"

    def symbols(self) -> list[str]:
        """Return list of all symbols in this slice."""
        return list(self._data.keys())

    def has(self, symbol: str) -> bool:
        """Check whether this slice includes a given symbol."""
        return symbol in self._data

    def bar(self, symbol: str) -> Optional[Bar]:
        """Return the full Bar for a symbol, or None if missing."""
        return self._data.get(symbol)

    def open(self, symbol: str) -> Optional[float]:
        """Return the open price for a symbol, or None if missing."""
        b = self._data.get(symbol)
        return b.open if b is not None else None

    def high(self, symbol: str) -> Optional[float]:
        """Return the high price for a symbol, or None if missing."""
        b = self._data.get(symbol)
        return b.high if b is not None else None

    def low(self, symbol: str) -> Optional[float]:
        """Return the low price for a symbol, or None if missing."""
        b = self._data.get(symbol)
        return b.low if b is not None else None

    def close(self, symbol: str) -> Optional[float]:
        """Return the close price for a symbol, or None if missing."""
        b = self._data.get(symbol)
        return b.close if b is not None else None

    def volume(self, symbol: str) -> Optional[float]:
        """Return the volume for a symbol, or None if missing."""
        b = self._data.get(symbol)
        return b.volume if b is not None else None

    def alt_series(self, series_id: str) -> AltSeries:
        """Return the point-in-time snapshot of alt-data history for a series."""
        return self._alt_history.get(series_id, MappingProxyType({}))

    def alt_value(self, series_id: str) -> Optional[float]:
        """Return the latest value for an alternative data series."""
        series = self.alt_series(series_id)
        if not series:
            return None
        return series[max(series)]

@dataclass(frozen=True)
class PortfolioView:
    """Read-only snapshot of the strategy's current portfolio state."""
    equity: float                    # total value of the strategy's portfolio
    cash: float                      # available, unallocated cash
    positions: Mapping[str, float]   # quantity of each symbol
    weights: Mapping[str, float]     # current portfolio weights (by value)

    def __post_init__(self) -> None:
        object.__setattr__(self, 'positions', MappingProxyType(dict(self.positions)))
        object.__setattr__(self, 'weights', MappingProxyType(dict(self.weights)))

class Signal:
    """Base class for all strategy signals returned by on_data()."""

@dataclass(frozen=True)
class TargetWeights(Signal):
    """
    Set the portfolio to the given target weights.

    - Symbols present in `weights` are sized to the specified fraction of portfolio equity. 
    - Symbols absent from `weights` are sold to zero.
    - Weights summing to less than 1.0 leave the remainder in cash.
    
    Raises:
        ValueError: If any weight is negative or weights sum above 1.0.
        Bad input are likely a logic/math ERROR, not something we should try to clamp or normalize. 
    """
    weights: Mapping[str, float]

    def __post_init__(self) -> None:
        negative = {s: w for s, w in self.weights.items() if w < 0}
        if negative:
            raise ValueError(f"Negative weights are not allowed: {negative}")
        total = sum(self.weights.values())
        if total > 1.0 + 1e-7:
            raise ValueError(
                f"Weights sum to {total:.6f}, which exceeds 1.0. "
                "Use weights that sum to at most 1.0 (remainder is held as cash)."
            )
        
        # freeze after validation
        object.__setattr__(self, 'weights', MappingProxyType(dict(self.weights)))

class Hold(Signal):
    """
    Keep the current portfolio unchanged this bar.
    """

class Liquidate(Signal):
    """
    Sell all positions and move fully to cash.
    """