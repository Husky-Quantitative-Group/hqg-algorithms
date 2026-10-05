# hqg-algorithms

Interfaces and helper types for writing HQG trading strategies.

## Install

```shell
python3 -m pip install --upgrade pip setuptools wheel
pip install hqg-algorithms
```

## Quick start

Subclass `Strategy`, declare your `universe` and `cadence`, and implement `on_data`:

```python
from hqg_algorithms import (
    Strategy, Cadence, Slice, PortfolioView,
    BarSize, ExecutionTiming, Signal, TargetWeights,
)

class BuyAndRebalance(Strategy):
    universe = ["SPY", "IEF"]
    cadence = Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_CLOSE)

    def on_data(self, data: Slice, portfolio: PortfolioView) -> Signal:
        return TargetWeights({"SPY": 0.6, "IEF": 0.4})
```

| Declaration | Purpose | Required? |
| -------- | --------- | --------- |
| `universe` | List of ticker strings the platform loads for this strategy | Yes |
| `alt_data` | Optional list of provider-prefixed alternative data series IDs | No |
| `cadence` | Bar resolution and execution timing (optional - defaults to daily, close-to-close) | No |
| `on_data()` | Return a `Signal`: `TargetWeights(...)`, `Hold()`, or `Liquidate()` | Yes |

### Important constraints

- `universe` **must** be a non-empty list literal of ticker strings (e.g. `["SPY", "IEF"]`). Variables, function calls, and concatenation are not supported. Tickers are normalized to uppercase and deduplicated. Empty strings, whitespace-only tickers, and tickers exceeding 12 characters are rejected. Maximum universe size is 200.
- `alt_data` is optional and, if present, **must** be a list literal of provider-prefixed series IDs such as `["FRED.GDP", "FRED.DGS10"]`. IDs are normalized to uppercase and deduplicated. Each ID must be in `PROVIDER.SERIES` form with non-empty dot-separated segments containing only letters, digits, underscores, or hyphens. Empty strings, whitespace-only IDs, IDs exceeding 100 characters, and lists with more than 100 unique valid IDs are rejected. The 100-character ID limit and 100-series count limit are arbitrary safety caps.
- `cadence` **must** be a direct `Cadence(...)` call with `BarSize.X` and/or `ExecutionTiming.Y` keyword arguments. Positional arguments and unknown keyword arguments are rejected. If omitted, it defaults to `Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_CLOSE)`.
- `universe`, `alt_data`, and `cadence` are fixed at class definition and cannot be changed at runtime.

`Slice` maps each symbol to a `Bar` dataclass with typed fields (`open`, `high`, `low`, `close`, `volume`). You can access prices via helpers like `data.close("SPY")`, or grab the full bar with `data.bar("SPY")` for direct attribute access. `PortfolioView` gives read-only access to current equity, cash, positions, and weights.

### Using alternative data

If your strategy declares `alt_data`, each `Slice` also carries a point-in-time view of those series, accessible through two methods:

| Method | Returns |
| --- | --- |
| `data.alt_value("FRED.GDP")` | The single most recently known value for the series, or `None` if nothing is known yet. |
| `data.alt_series("FRED.GDP")` | Every observation period known so far, as `{period: value}`, for trend/lookback calculations. |

```python
gdp = data.alt_value("FRED.GDP")
if gdp is not None:
    ...
```

**What "point-in-time" means in practice:**
- The keys returned by `alt_series()` are the **observation period** the value describes (e.g. the start of a fiscal quarter for GDP) — not the date the value was published.
- Both methods only ever reflect what was actually knowable as of the current bar. A later revision to an old period is never visible before the bar on which it was actually released — your strategy cannot see the future, including future revisions of past data.
- Series may update infrequently. A quarterly series like GDP will return the **same value across many consecutive bars** until a new release or revision lands — this is expected.
- If a series has no data yet for the current date range (e.g. the backtest starts before the series' first release), both methods return empty/`None` rather than raising — always check for `None`/empty before using the result.
### Execution timing

`ExecutionTiming` controls when your strategy receives data and when the resulting trades fill. Pick the option that matches your signal logic:

| `ExecutionTiming` | `on_data` fires at | Trades fill at |
| --- | --- | --- |
| `CLOSE_TO_CLOSE` | Bar close | Same bar's close (DEFAULT) |
| `CLOSE_TO_NEXT_OPEN` | Bar close | Next bar's open |

`CLOSE_TO_NEXT_OPEN` is the most realistic for intraday strategies since it avoids look-ahead bias - your signal only uses data that was already available before the trade executes.

### Signal types

`on_data()` returns a `Signal` that tells the backtester what to do:

| Signal | Meaning |
| -------- | --------- |
| `TargetWeights({"SPY": 0.6, "IEF": 0.4})` | Rebalance to these weights. Omitted symbols are sold to zero. Weights summing to less than 1.0 leave the remainder in cash. |
| `Hold()` | Keep the current allocation unchanged. |
| `Liquidate()` | Sell all positions and move fully to cash. |

## Validating and parsing strategies

The `parsing` module provides two functions for working with strategy source code without executing it. Both use AST parsing - no user code is ever run.

### `validate_strategy`

Checks strategy source code and returns a list of error strings. An empty list means the strategy is valid.

```python
from hqg_algorithms import validate_strategy

source = open("my_strategy.py").read()
errors = validate_strategy(source)

if errors:
    for e in errors:
        print(f"❌ {e}")
else:
    print("✅ Strategy is valid")
```

| Check | Rule |
| --- | --- |
| **Syntax** | Source must be parseable Python |
| **Strategy class** | At least one class inheriting from `Strategy` must be present |
| **`universe`** | Must be a non-empty list literal of valid ticker strings |
| **`alt_data`** | If present, must be a list literal of valid provider-prefixed series IDs |
| **`cadence`** | If present, must be a `Cadence(...)` call with valid keyword args only |
| **`on_data`** | Must be defined as a method on the strategy class |

All errors are blocking - if `validate_strategy` returns anything, the strategy cannot run.

### `get_strategy_metadata`

Extracts `universe`, `alt_data`, and `cadence` as typed objects. Raises `ValueError` if the source is invalid.

```python
from hqg_algorithms import get_strategy_metadata

meta = get_strategy_metadata(source)
print(meta.universe)   # ["SPY", "IEF"] (normalized, deduplicated)
print(meta.alt_data)   # ["FRED.GDP"] (normalized, deduplicated)

print(meta.cadence)    # Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_CLOSE)
```

Returns a frozen `StrategyMetadata` dataclass:

```python
@dataclass(frozen=True)
class StrategyMetadata:
    universe: list[str]
    cadence: Cadence
    alt_data: list[str]
```

This is intended for services that need to know what a strategy requires (data subscriptions, scheduling) without loading it.

## Example - SMA crossover

```python
from hqg_algorithms import (
    Strategy, Cadence, Slice, PortfolioView,
    BarSize, ExecutionTiming, Signal, TargetWeights, Hold,
)
from collections import deque


class SimpleSMA(Strategy):
    """Go risk-on when SPY is above its 21-day mean, otherwise hold bonds."""

    universe = ["SPY", "BND"]
    cadence = Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_CLOSE)

    def __init__(self):
        self._window = 21
        self._q: deque[float] = deque(maxlen=self._window)

    def on_data(self, data: Slice, portfolio: PortfolioView) -> Signal:
        spy_close = data.close("SPY")
        if spy_close is None:
            return Hold()

        self._q.append(spy_close)

        if len(self._q) < self._window:
            return TargetWeights({"BND": 1.0})  # hold bonds while warming up

        sma = sum(self._q) / len(self._q)

        if spy_close > sma:
            return TargetWeights({"SPY": 0.5, "BND": 0.5})  # uptrend
        return TargetWeights({"BND": 1.0})                   # downtrend
```
## Example 2 - Macro Gated GDP allocation

```python
from hqg_algorithms import (
    Strategy, Cadence, Slice, PortfolioView,
    BarSize, ExecutionTiming, Signal, TargetWeights, Hold,
)


class MacroGatedAllocation(Strategy):
    """Stay invested in equities only while GDP is trending up; move to
    bonds otherwise. Demonstrates combining securities and alt data."""

    universe = ["SPY", "IEF"]
    alt_data = ["FRED.GDP"]
    cadence = Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_CLOSE)

    def on_data(self, data: Slice, portfolio: PortfolioView) -> Signal:
        gdp_history = data.alt_series("FRED.GDP")

        if len(gdp_history) < 2:
            return Hold()  # not enough history yet to compute a trend

        # last two known quarters, oldest first
        recent = sorted(gdp_history.items())[-2:]
        previous_value, latest_value = recent[0][1], recent[1][1]

        if latest_value > previous_value:
            return TargetWeights({"SPY": 0.7, "IEF": 0.3})  # growing
        return TargetWeights({"SPY": 0.3, "IEF": 0.7})      # contracting
```
## Additional docs

- Publishing workflow and release checklist: [`docs/publishing.md`](docs/publishing.md)
