# hqg-algorithms

Interfaces and helper types for writing HQG trading strategies.

## Install
```shell
python3 -m pip install --upgrade pip setuptools wheel
pip install hqg-algorithms
```

## Implement a strategy
Subclass `Strategy` and implement the three abstract methods the backtester calls.


Example:

```python
from datetime import timedelta
from hqg_algorithms import Strategy, Cadence, Slice, PortfolioView


class BuyAndRebalanceSpyIef(Strategy):
    def universe(self) -> list[str]:
        return ["SPY", "IEF"]

    def cadence(self) -> Cadence:
        return Cadence( 
            bar_size=timedelta(days=1), # default
            call_phase="on_bar_close", # default
            exec_lag_bars=1, # default
        )

    def on_data(self, data: Slice, portfolio: PortfolioView) -> dict[str, float] | None:
        # Rebalance daily
        return {"SPY": 0.6, "IEF": 0.4}
```

Key lifecycle methods:
- `universe()` tells the platform which symbols to load.
- `cadence()` specifies call frequency, trigger phase, and execution lag.
- `on_data(data, portfolio)` returns target portfolio weights, `{}` for all cash, or `None` to skip an update.

`Slice` exposes helper methods like `slice.close(symbol)` to inspect prices, while `PortfolioView` gives read-only access to current holdings and weights.

## Additional docs
- Publishing workflow and release checklist: `docs/publishing.md`
