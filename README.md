# hqg-algorithms

Interfaces and helper types for writing HQG trading strategies.

## Install
```shell
python3 -m pip install --upgrade pip setuptools wheel
pip install hqg-algorithms
```

## Quick start

Subclass `Strategy` and implement three methods:
```python
from hqg_algorithms import Strategy, Cadence, Slice, PortfolioView, BarSize, CallPhase


class BuyAndRebalance(Strategy):
    def universe(self) -> list[str]:
        return ["SPY", "IEF"]

    def cadence(self) -> Cadence:
        return Cadence(bar_size=BarSize.DAILY, call_phase=CallPhase.ON_BAR_CLOSE)

    def on_data(self, data: Slice, portfolio: PortfolioView) -> dict[str, float] | None:
        return {"SPY": 0.6, "IEF": 0.4}
```

| Method | Purpose |
|--------|---------|
| `universe()` | Symbols the platform loads for this strategy |
| `cadence()` | Bar resolution, trigger timing, and execution delay |
| `on_data()` | Return target portfolio weights, `{}` for all cash, or `None` to skip an update |

`Slice` maps each symbol to a `Bar` dataclass with typed fields (`open`, `high`, `low`, `close`, `volume`). You can access prices via helpers like `data.close("SPY")`, or grab the full bar with `data.bar("SPY")` for direct attribute access. `PortfolioView` gives read-only access to current equity, cash, positions, and weights.

## Example — SMA crossover
```python
from hqg_algorithms import Strategy, Cadence, Slice, PortfolioView, BarSize, CallPhase
from collections import deque


class SimpleSMA(Strategy):
    """Go risk-on when SPY is above its 21-day mean, otherwise hold bonds."""

    def __init__(self):
        self._window = 21
        self._q: deque[float] = deque(maxlen=self._window)

    def universe(self) -> list[str]:
        return ["SPY", "BND"]

    def cadence(self) -> Cadence:
        return Cadence(bar_size=BarSize.DAILY, call_phase=CallPhase.ON_BAR_CLOSE)

    def on_data(self, data: Slice, portfolio: PortfolioView) -> dict[str, float] | None:
        spy_close = data.close("SPY")
        if spy_close is None:
            return None

        self._q.append(spy_close)

        if len(self._q) < self._window:
            return {"BND": 1.0}  # hold bonds while warming up

        sma = sum(self._q) / len(self._q)

        if spy_close > sma:
            return {"SPY": 0.5, "BND": 0.5}  # uptrend
        return {"BND": 1.0}                  # downtrend
```

## Additional docs

- Publishing workflow and release checklist: [`docs/publishing.md`](docs/publishing.md)