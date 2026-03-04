"""test_types.py - verify all read-only protections on types."""

import pytest
from hqg_algorithms import (
    Bar, Slice, PortfolioView, TargetWeights, Hold, Liquidate,
    Cadence, BarSize, ExecutionTiming,
)


# ── Fixtures ─────────────────────────────────────────────────────────

@pytest.fixture
def bar():
    return Bar(open=100.0, high=105.0, low=99.0, close=104.0, volume=1e6)


@pytest.fixture
def slice_data(bar):
    return Slice({"SPY": bar, "IEF": Bar(open=97.0, high=97.5, low=96.8, close=97.3, volume=4e6)})


@pytest.fixture
def portfolio():
    return PortfolioView(
        equity=100_000.0,
        cash=20_000.0,
        positions={"SPY": 100, "IEF": 200},
        weights={"SPY": 0.6, "IEF": 0.4},
    )


# ── Bar (frozen dataclass) ──────────────────────────────────────────

class TestBarImmutability:
    def test_cannot_set_attribute(self, bar):
        with pytest.raises(AttributeError):
            bar.open = 999.0

    def test_cannot_set_any_field(self, bar):
        for field in ("open", "high", "low", "close", "volume"):
            with pytest.raises(AttributeError):
                setattr(bar, field, 0.0)

    def test_cannot_delete_attribute(self, bar):
        with pytest.raises(AttributeError):
            del bar.open

    def test_cannot_add_new_attribute(self, bar):
        with pytest.raises(AttributeError):
            bar.vwap = 102.0


# ── Slice (Mapping-based, read-only) ────────────────────────────────

class TestSliceReadAccess:
    def test_getitem(self, slice_data, bar):
        assert slice_data["SPY"] == bar

    def test_get_missing_returns_none(self, slice_data):
        assert slice_data.get("AAPL") is None

    def test_contains(self, slice_data):
        assert "SPY" in slice_data
        assert "AAPL" not in slice_data

    def test_len(self, slice_data):
        assert len(slice_data) == 2

    def test_iter(self, slice_data):
        assert set(slice_data) == {"SPY", "IEF"}

    def test_keys_values_items(self, slice_data):
        assert set(slice_data.keys()) == {"SPY", "IEF"}
        assert len(list(slice_data.values())) == 2
        assert len(list(slice_data.items())) == 2

    def test_symbols(self, slice_data):
        assert set(slice_data.symbols()) == {"SPY", "IEF"}

    def test_has(self, slice_data):
        assert slice_data.has("SPY")
        assert not slice_data.has("AAPL")

    def test_bar(self, slice_data, bar):
        assert slice_data.bar("SPY") == bar
        assert slice_data.bar("AAPL") is None

    def test_ohlcv_helpers(self, slice_data):
        assert slice_data.open("SPY") == 100.0
        assert slice_data.high("SPY") == 105.0
        assert slice_data.low("SPY") == 99.0
        assert slice_data.close("SPY") == 104.0
        assert slice_data.volume("SPY") == 1e6

    def test_ohlcv_helpers_missing(self, slice_data):
        assert slice_data.open("AAPL") is None
        assert slice_data.close("AAPL") is None


class TestSliceImmutability:
    def test_cannot_setitem(self, slice_data, bar):
        with pytest.raises(TypeError):
            slice_data["AAPL"] = bar

    def test_cannot_delitem(self, slice_data):
        with pytest.raises(TypeError):
            del slice_data["SPY"]

    def test_no_pop(self, slice_data):
        assert not hasattr(slice_data, "pop")

    def test_no_clear(self, slice_data):
        assert not hasattr(slice_data, "clear")

    def test_no_update(self, slice_data):
        assert not hasattr(slice_data, "update")

    def test_no_setdefault(self, slice_data):
        assert not hasattr(slice_data, "setdefault")

    def test_no_popitem(self, slice_data):
        assert not hasattr(slice_data, "popitem")

    def test_no_ior(self, slice_data, bar):
        with pytest.raises(TypeError):
            slice_data |= {"AAPL": bar}

    def test_caller_mutation_does_not_affect_slice(self):
        original = {"SPY": Bar(open=1, high=2, low=0.5, close=1.5, volume=100)}
        s = Slice(original)
        original["AAPL"] = Bar(open=9, high=9, low=9, close=9, volume=9)
        assert "AAPL" not in s
        assert len(s) == 1


# ── PortfolioView (frozen dataclass + MappingProxyType) ─────────────

class TestPortfolioViewImmutability:
    def test_cannot_set_equity(self, portfolio):
        with pytest.raises(AttributeError):
            portfolio.equity = 999.0

    def test_cannot_set_cash(self, portfolio):
        with pytest.raises(AttributeError):
            portfolio.cash = 999.0

    def test_cannot_reassign_positions(self, portfolio):
        with pytest.raises(AttributeError):
            portfolio.positions = {}

    def test_cannot_reassign_weights(self, portfolio):
        with pytest.raises(AttributeError):
            portfolio.weights = {}

    def test_cannot_mutate_positions_dict(self, portfolio):
        with pytest.raises(TypeError):
            portfolio.positions["SPY"] = 9999

    def test_cannot_mutate_weights_dict(self, portfolio):
        with pytest.raises(TypeError):
            portfolio.weights["SPY"] = 0.99

    def test_no_pop_positions(self, portfolio):
        assert not hasattr(portfolio.positions, "pop")

    def test_no_clear_weights(self, portfolio):
        assert not hasattr(portfolio.weights, "clear")

    def test_no_update_positions(self, portfolio):
        assert not hasattr(portfolio.positions, "update")

    def test_cannot_delete_positions_key(self, portfolio):
        with pytest.raises(TypeError):
            del portfolio.positions["SPY"]

    def test_caller_mutation_does_not_affect_portfolio(self):
        pos = {"SPY": 100}
        wts = {"SPY": 1.0}
        pv = PortfolioView(equity=50_000, cash=0, positions=pos, weights=wts)
        pos["AAPL"] = 200
        wts["AAPL"] = 0.5
        assert "AAPL" not in pv.positions
        assert "AAPL" not in pv.weights

    def test_read_access_works(self, portfolio):
        assert portfolio.equity == 100_000.0
        assert portfolio.cash == 20_000.0
        assert portfolio.positions["SPY"] == 100
        assert portfolio.weights["IEF"] == 0.4


# ── TargetWeights (frozen + validation + MappingProxyType) ──────────

class TestTargetWeightsValidation:
    def test_valid_weights(self):
        tw = TargetWeights(weights={"SPY": 0.6, "IEF": 0.4})
        assert tw.weights["SPY"] == 0.6

    def test_weights_under_one_ok(self):
        tw = TargetWeights(weights={"SPY": 0.3})
        assert tw.weights["SPY"] == 0.3

    def test_empty_weights_ok(self):
        tw = TargetWeights(weights={})
        assert len(tw.weights) == 0

    def test_negative_weight_raises(self):
        with pytest.raises(ValueError, match="Negative"):
            TargetWeights(weights={"SPY": -0.1})

    def test_weights_exceeding_one_raises(self):
        with pytest.raises(ValueError, match="exceeds 1.0"):
            TargetWeights(weights={"SPY": 0.6, "IEF": 0.5})


class TestTargetWeightsImmutability:
    def test_cannot_reassign_weights(self):
        tw = TargetWeights(weights={"SPY": 0.5})
        with pytest.raises(AttributeError):
            tw.weights = {"IEF": 1.0}

    def test_cannot_mutate_weights_dict(self):
        tw = TargetWeights(weights={"SPY": 0.5})
        with pytest.raises(TypeError):
            tw.weights["SPY"] = -1.0

    def test_cannot_add_to_weights_dict(self):
        tw = TargetWeights(weights={"SPY": 0.5})
        with pytest.raises(TypeError):
            tw.weights["AAPL"] = 0.3

    def test_no_pop_weights(self):
        tw = TargetWeights(weights={"SPY": 0.5})
        assert not hasattr(tw.weights, "pop")

    def test_caller_mutation_does_not_bypass_validation(self):
        w = {"SPY": 0.5}
        tw = TargetWeights(weights=w)
        w["SPY"] = -99.0
        assert tw.weights["SPY"] == 0.5


# ── Cadence (frozen dataclass) ──────────────────────────────────────

class TestCadenceImmutability:
    def test_cannot_set_bar_size(self):
        c = Cadence()
        with pytest.raises(AttributeError):
            c.bar_size = BarSize.WEEKLY

    def test_cannot_set_execution(self):
        c = Cadence()
        with pytest.raises(AttributeError):
            c.execution = ExecutionTiming.CLOSE_TO_CLOSE


# ── Hold / Liquidate ────────────────────────────────────────────────

class TestSignalTypes:
    def test_hold_instantiates(self):
        assert Hold() is not None

    def test_liquidate_instantiates(self):
        assert Liquidate() is not None
