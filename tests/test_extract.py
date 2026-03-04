"""test_parsing_metadata.py - verify get_strategy_metadata extraction."""

import pytest
from hqg_algorithms import get_strategy_metadata, StrategyMetadata, BarSize, ExecutionTiming, Cadence


# ── Valid strategies ─────────────────────────────────────────────────

class TestValidStrategies:
    def test_full_definition(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY", "IEF", "GLD"]
    cadence = Cadence(bar_size=BarSize.WEEKLY, execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY", "IEF", "GLD"]
        assert meta.cadence.bar_size == BarSize.WEEKLY
        assert meta.cadence.execution == ExecutionTiming.CLOSE_TO_NEXT_OPEN

    def test_cadence_omitted_uses_defaults(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["AAPL"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["AAPL"]
        assert meta.cadence == Cadence()
        assert meta.cadence.bar_size == BarSize.DAILY
        assert meta.cadence.execution == ExecutionTiming.CLOSE_TO_CLOSE

    def test_cadence_no_args_uses_defaults(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence()

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.cadence == Cadence()

    def test_cadence_bar_size_only(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.MONTHLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.cadence.bar_size == BarSize.MONTHLY
        assert meta.cadence.execution == ExecutionTiming.CLOSE_TO_CLOSE

    def test_cadence_execution_only(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.cadence.bar_size == BarSize.DAILY
        assert meta.cadence.execution == ExecutionTiming.CLOSE_TO_NEXT_OPEN

    @pytest.mark.parametrize("bar_size", ["DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"])
    def test_all_bar_sizes(self, bar_size):
        meta = get_strategy_metadata(f"""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.{bar_size})

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.cadence.bar_size == BarSize[bar_size]

    @pytest.mark.parametrize("execution", ["CLOSE_TO_CLOSE", "CLOSE_TO_NEXT_OPEN"])
    def test_all_execution_timings(self, execution):
        meta = get_strategy_metadata(f"""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.{execution})

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.cadence.execution == ExecutionTiming[execution]

    def test_single_ticker(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["AAPL"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["AAPL"]

    def test_many_tickers(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA", "NVDA", "BRK-B"]

    def on_data(self, data, portfolio):
        pass
""")
        assert len(meta.universe) == 8

    def test_extra_class_attributes_ignored(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    some_param = 42
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.DAILY)
    name = "my strat"

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY"]

    def test_strategy_with_imports_and_comments(self):
        meta = get_strategy_metadata("""
# A momentum strategy
from hqg_algorithms import Strategy, Cadence, BarSize, ExecutionTiming

class MyStrategy(Strategy):
    universe = ["SPY", "IEF"]
    cadence = Cadence(bar_size=BarSize.WEEKLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY", "IEF"]
        assert meta.cadence.bar_size == BarSize.WEEKLY


# ── Return type ──────────────────────────────────────────────────────

class TestReturnType:
    def test_returns_strategy_metadata(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert isinstance(meta, StrategyMetadata)

    def test_metadata_is_frozen(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        with pytest.raises(AttributeError):
            meta.universe = ["AAPL"]


# ── Annotated assignments ────────────────────────────────────────────

class TestAnnotatedAssign:
    def test_annotated_universe(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe: list[str] = ["SPY", "IEF"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY", "IEF"]

    def test_annotated_cadence(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence: Cadence = Cadence(bar_size=BarSize.WEEKLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.cadence.bar_size == BarSize.WEEKLY

    def test_annotated_both(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe: list[str] = ["SPY", "IEF"]
    cadence: Cadence = Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY", "IEF"]
        assert meta.cadence.execution == ExecutionTiming.CLOSE_TO_NEXT_OPEN


# ── Universe normalization ───────────────────────────────────────────

class TestUniverseNormalization:
    def test_uppercases_tickers(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["aapl", "msft"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["AAPL", "MSFT"]

    def test_strips_whitespace(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["  AAPL  ", " MSFT"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["AAPL", "MSFT"]

    def test_deduplicates(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY", "spy", "SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY"]

    def test_deduplicates_after_normalization(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["aapl", "AAPL", " aapl "]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["AAPL"]

    def test_preserves_order_first_occurrence(self):
        meta = get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["IEF", "SPY", "GLD", "SPY", "IEF"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["IEF", "SPY", "GLD"]


# ── Strategy base class detection ────────────────────────────────────

class TestStrategyDetection:
    def test_helper_class_before_strategy(self):
        meta = get_strategy_metadata("""
class Config:
    universe = ["not", "a", "strategy"]

class MyStrategy(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY"]

    def test_module_qualified_base(self):
        meta = get_strategy_metadata("""
class MyStrategy(hqg_algorithms.Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY"]

    def test_multiple_bases(self):
        meta = get_strategy_metadata("""
class MyStrategy(SomeMixin, Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY"]

    def test_first_strategy_class_wins(self):
        meta = get_strategy_metadata("""
class First(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass

class Second(Strategy):
    universe = ["AAPL", "MSFT"]

    def on_data(self, data, portfolio):
        pass
""")
        assert meta.universe == ["SPY"]


# ── Errors: no strategy found ───────────────────────────────────────

class TestNoStrategyFound:
    def test_empty_source(self):
        with pytest.raises(ValueError, match="No strategy class"):
            get_strategy_metadata("")

    def test_no_class(self):
        with pytest.raises(ValueError, match="No strategy class"):
            get_strategy_metadata("x = 1\ny = 2\n")

    def test_class_without_strategy_base(self):
        with pytest.raises(ValueError, match="No strategy class"):
            get_strategy_metadata("""
class NotAStrategy:
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")


# ── Errors: syntax ──────────────────────────────────────────────────

class TestSyntaxError:
    def test_invalid_python(self):
        with pytest.raises(ValueError, match="Syntax error"):
            get_strategy_metadata("def foo(:")

    def test_unclosed_bracket(self):
        with pytest.raises(ValueError, match="Syntax error"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY", "IEF"
""")


# ── Errors: bad universe ────────────────────────────────────────────

class TestBadUniverse:
    def test_universe_is_string(self):
        with pytest.raises(ValueError, match="list"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = "AAPL"

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_is_int(self):
        with pytest.raises(ValueError, match="list"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = 42

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_is_tuple(self):
        with pytest.raises(ValueError, match="list"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ("SPY", "IEF")

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_empty(self):
        with pytest.raises(ValueError, match="empty"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = []

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_has_non_string_elements(self):
        with pytest.raises(ValueError, match="string"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["AAPL", 123]

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_is_function_call(self):
        with pytest.raises(ValueError, match="list literal"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = get_sp500()

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_is_variable(self):
        with pytest.raises(ValueError, match="list literal"):
            get_strategy_metadata("""
TICKERS = ["AAPL"]

class MyStrategy(Strategy):
    universe = TICKERS

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_is_concatenation(self):
        with pytest.raises(ValueError, match="list literal"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["AAPL"] + ["MSFT"]

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_is_comprehension(self):
        with pytest.raises(ValueError, match="list literal"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = [f"T{i}" for i in range(10)]

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_missing(self):
        with pytest.raises(ValueError, match="(?i)universe"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    cadence = Cadence()

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_whitespace_ticker(self):
        with pytest.raises(ValueError, match="empty|whitespace"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY", "  "]

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_ticker_too_long(self):
        with pytest.raises(ValueError, match="exceeds"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["THISISSUPERLONGTICKER"]

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_all_invalid_tickers(self):
        with pytest.raises(ValueError):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["", "   "]

    def on_data(self, data, portfolio):
        pass
""")

    def test_universe_exceeds_max_size(self):
        tickers = ", ".join(f'"T{i:04d}"' for i in range(201))
        with pytest.raises(ValueError, match="max|200"):
            get_strategy_metadata(f"""
class MyStrategy(Strategy):
    universe = [{tickers}]

    def on_data(self, data, portfolio):
        pass
""")


# ── Errors: bad cadence ─────────────────────────────────────────────

class TestBadCadence:
    def test_cadence_is_string(self):
        with pytest.raises(ValueError, match="Cadence"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = "1d"

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_is_dict(self):
        with pytest.raises(ValueError, match="Cadence"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = {"bar_size": "1d"}

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_wrong_function(self):
        with pytest.raises(ValueError, match="Cadence"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = NotCadence(bar_size=BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_invalid_bar_size(self):
        with pytest.raises(ValueError, match="bar_size"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.HOURLY)

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_invalid_execution(self):
        with pytest.raises(ValueError, match="execution"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.FAKE)

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_removed_open_to_open(self):
        with pytest.raises(ValueError, match="execution"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.OPEN_TO_OPEN)

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_arg_is_variable(self):
        with pytest.raises(ValueError, match="BarSize"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=my_var)

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_arg_is_string_literal(self):
        with pytest.raises(ValueError, match="BarSize"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size="1d")

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_positional_args(self):
        with pytest.raises(ValueError, match="(?i)positional|keyword"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_unknown_kwarg(self):
        with pytest.raises(ValueError, match="(?i)unknown|foo"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(foo=BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")

    def test_cadence_misspelled_kwarg(self):
        with pytest.raises(ValueError, match="barsize"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(barsize=BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")


# ── Errors: missing on_data ─────────────────────────────────────────

class TestMissingOnData:
    def test_no_on_data(self):
        with pytest.raises(ValueError, match="on_data"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]
""")

    def test_on_data_misspelled(self):
        with pytest.raises(ValueError, match="on_data"):
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def ondata(self, data, portfolio):
        pass
""")


# ── Error message quality ───────────────────────────────────────────

class TestErrorMessages:
    def test_multiple_errors_all_reported(self):
        """get_strategy_metadata should surface all validation errors, not just the first."""
        with pytest.raises(ValueError) as exc_info:
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = 42
    cadence = "daily"
""")
        msg = str(exc_info.value)
        assert "list" in msg
        assert "Cadence" in msg
        assert "on_data" in msg

    def test_error_message_includes_all_bad_tickers(self):
        with pytest.raises(ValueError) as exc_info:
            get_strategy_metadata("""
class MyStrategy(Strategy):
    universe = ["", "THISISSUPERLONGTICKER", "   "]

    def on_data(self, data, portfolio):
        pass
""")
        msg = str(exc_info.value)
        assert "universe[0]" in msg or "empty" in msg
        assert "exceeds" in msg