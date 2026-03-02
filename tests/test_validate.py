"""test_validate.py - verify AST-based strategy validation."""

import pytest
from hqg_algorithms import validate_strategy


# ── Valid strategies return no errors ────────────────────────────────

class TestValid:
    def test_full_definition(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY", "IEF", "GLD"]
    cadence = Cadence(bar_size=BarSize.WEEKLY, execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_minimal_no_cadence(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["AAPL"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_cadence_no_args(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence()

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_cadence_bar_size_only(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.MONTHLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_cadence_execution_only(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_extra_class_attributes_ignored(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    some_param = 42
    name = "test"

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_many_tickers(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["AAPL", "MSFT", "GOOG", "AMZN", "META", "TSLA", "NVDA", "BRK-B"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    @pytest.mark.parametrize("bar_size", ["DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"])
    def test_all_valid_bar_sizes(self, bar_size):
        errors = validate_strategy(f"""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.{bar_size})

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    @pytest.mark.parametrize("execution", ["CLOSE_TO_CLOSE", "CLOSE_TO_NEXT_OPEN"])
    def test_all_valid_execution_timings(self, execution):
        errors = validate_strategy(f"""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.{execution})

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_on_data_with_extra_methods(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def helper(self):
        pass

    def on_data(self, data, portfolio):
        pass

    def another_helper(self):
        pass
""")
        assert errors == []

    def test_on_data_as_async(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    async def on_data(self, data, portfolio):
        pass
""")
        assert errors == []


# ── Annotated assignments (ast.AnnAssign) ────────────────────────────

class TestAnnotatedAssign:
    def test_annotated_universe(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe: list[str] = ["SPY", "IEF"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_annotated_cadence(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence: Cadence = Cadence(bar_size=BarSize.WEEKLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_annotated_both(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe: list[str] = ["SPY", "IEF"]
    cadence: Cadence = Cadence(bar_size=BarSize.DAILY, execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_annotation_only_no_value_is_missing(self):
        """universe: list[str] without assignment should be treated as missing."""
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe: list[str]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("universe" in e.lower() or "missing" in e.lower() for e in errors)

    def test_annotated_bad_universe_type(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe: str = "AAPL"

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list" in e for e in errors)


# ── Strategy base class detection ────────────────────────────────────

class TestStrategyDetection:
    def test_helper_class_with_universe_before_strategy(self):
        """Should skip non-Strategy classes even if they have universe."""
        errors = validate_strategy("""
class Config:
    universe = ["not", "a", "strategy"]

class MyStrategy(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_helper_class_with_universe_only(self):
        """Class with universe but not inheriting Strategy should not be found."""
        errors = validate_strategy("""
class NotAStrategy:
    universe = ["SPY", "IEF"]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("No strategy class" in e for e in errors)

    def test_module_qualified_strategy_base(self):
        """class MyStrategy(hqg_algorithms.Strategy) should be detected."""
        errors = validate_strategy("""
class MyStrategy(hqg_algorithms.Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_multiple_bases_with_strategy(self):
        errors = validate_strategy("""
class MyStrategy(SomeMixin, Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_multiple_strategy_classes_validates_first(self):
        """If multiple Strategy subclasses exist, validate the first one."""
        errors = validate_strategy("""
class First(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass

class Second(Strategy):
    universe = 42
""")
        assert errors == []

    def test_universe_in_init_not_detected(self):
        """self.universe = [...] inside __init__ should not count."""
        errors = validate_strategy("""
class MyStrategy(Strategy):
    def __init__(self):
        self.universe = ["SPY"]
    def on_data(self, data, portfolio):
        pass
""")
        assert any("universe" in e.lower() or "missing" in e.lower() for e in errors)


# ── No strategy found ────────────────────────────────────────────────

class TestNoStrategy:
    def test_empty_source(self):
        errors = validate_strategy("")
        assert len(errors) == 1
        assert "No strategy class" in errors[0]

    def test_no_class(self):
        errors = validate_strategy("x = 1\ny = 2\n")
        assert len(errors) == 1
        assert "No strategy class" in errors[0]

    def test_class_without_strategy_base(self):
        errors = validate_strategy("""
class Foo:
    x = 1
""")
        assert len(errors) == 1
        assert "No strategy class" in errors[0]

    def test_only_comments_and_imports(self):
        errors = validate_strategy("""
# this is a comment
import numpy as np
from hqg_algorithms import Strategy
""")
        assert any("No strategy class" in e for e in errors)


# ── Syntax errors ────────────────────────────────────────────────────

class TestSyntaxErrors:
    def test_invalid_python(self):
        errors = validate_strategy("def foo(:")
        assert len(errors) == 1
        assert "Syntax error" in errors[0]

    def test_unclosed_bracket(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY", "IEF"
""")
        assert len(errors) == 1
        assert "Syntax error" in errors[0]

    def test_indentation_error(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
universe = ["SPY"]
""")
        assert len(errors) == 1
        assert "Syntax error" in errors[0]


# ── Bad universe ─────────────────────────────────────────────────────

class TestBadUniverse:
    def test_universe_is_string(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = "AAPL"

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list" in e for e in errors)

    def test_universe_is_int(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = 42

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list" in e for e in errors)

    def test_universe_is_tuple(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ("SPY", "IEF")

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list" in e for e in errors)

    def test_universe_is_dict(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = {"SPY": 0.5}

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list" in e for e in errors)

    def test_universe_has_non_string_elements(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["AAPL", 123]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("string" in e for e in errors)

    def test_universe_has_mixed_types(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["AAPL", 123, None, True]

    def on_data(self, data, portfolio):
        pass
""")
        assert len([e for e in errors if "string" in e or "expected" in e]) >= 1

    def test_universe_empty(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = []

    def on_data(self, data, portfolio):
        pass
""")
        assert any("empty" in e for e in errors)

    def test_universe_is_function_call(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = get_sp500()

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list literal" in e for e in errors)

    def test_universe_is_variable(self):
        errors = validate_strategy("""
TICKERS = ["AAPL"]

class MyStrategy(Strategy):
    universe = TICKERS

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list literal" in e for e in errors)

    def test_universe_is_concatenation(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["AAPL"] + ["MSFT"]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list literal" in e for e in errors)

    def test_universe_is_comprehension(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = [f"STOCK_{i}" for i in range(10)]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("list literal" in e for e in errors)

    def test_universe_missing_from_strategy(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    cadence = Cadence()

    def on_data(self, data, portfolio):
        pass
""")
        assert any("universe" in e.lower() or "missing" in e.lower() for e in errors)


# ── Universe ticker cleaning ─────────────────────────────────────────

class TestUniverseCleaning:
    def test_empty_string_ticker(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = [""]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("empty" in e or "whitespace" in e for e in errors)

    def test_whitespace_only_ticker(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["   "]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("empty" in e or "whitespace" in e for e in errors)

    def test_ticker_exceeds_max_length(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["THISISSUPERLONGTICKER"]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("exceeds" in e or "characters" in e for e in errors)

    def test_ticker_at_max_length_ok(self):
        # MAX_TICKER_LEN = 12
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["ABCDEFGHIJKL"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_all_duplicates_yields_error(self):
        """["SPY", "SPY", "SPY"] → after dedup, still valid (1 ticker)."""
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY", "SPY", "SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_all_empty_strings(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["", "  ", ""]

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) >= 1

    def test_mix_valid_and_invalid_tickers(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY", "", "THISISSUPERLONGTICKER", "IEF"]

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) >= 2  # empty + too long

    def test_all_invalid_tickers_no_valid_remaining(self):
        """All tickers invalid → should get per-ticker errors + no valid tickers error."""
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["", "   "]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("no valid" in e.lower() or "empty" in e.lower() for e in errors)

    def test_universe_exceeds_max_size(self):
        tickers = ", ".join(f'"T{i:04d}"' for i in range(201))
        errors = validate_strategy(f"""
class MyStrategy(Strategy):
    universe = [{tickers}]

    def on_data(self, data, portfolio):
        pass
""")
        assert any("max" in e.lower() or "200" in e for e in errors)

    def test_universe_at_max_size_ok(self):
        tickers = ", ".join(f'"T{i:04d}"' for i in range(200))
        errors = validate_strategy(f"""
class MyStrategy(Strategy):
    universe = [{tickers}]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []


# ── Bad cadence ──────────────────────────────────────────────────────

class TestBadCadence:
    def test_cadence_is_string(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = "1d"

    def on_data(self, data, portfolio):
        pass
""")
        assert any("Cadence(...)" in e for e in errors)

    def test_cadence_is_dict(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = {"bar_size": "1d"}

    def on_data(self, data, portfolio):
        pass
""")
        assert any("Cadence(...)" in e for e in errors)

    def test_cadence_is_int(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = 5

    def on_data(self, data, portfolio):
        pass
""")
        assert any("Cadence(...)" in e for e in errors)

    def test_cadence_wrong_function(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = NotCadence(bar_size=BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("Cadence(...)" in e for e in errors)

    def test_cadence_invalid_bar_size(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.HOURLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("bar_size" in e for e in errors)

    def test_cadence_invalid_execution(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.FAKE)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("execution" in e for e in errors)

    def test_cadence_arg_is_variable(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=my_var)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("BarSize.X" in e or "ExecutionTiming.Y" in e for e in errors)

    def test_cadence_arg_is_string_literal(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size="1d")

    def on_data(self, data, portfolio):
        pass
""")
        assert any("BarSize.X" in e or "ExecutionTiming.Y" in e for e in errors)

    def test_cadence_arg_is_int_literal(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=1)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("BarSize.X" in e or "ExecutionTiming.Y" in e for e in errors)

    def test_cadence_arg_is_function_call(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=get_bar_size())

    def on_data(self, data, portfolio):
        pass
""")
        assert any("BarSize.X" in e or "ExecutionTiming.Y" in e for e in errors)

    def test_cadence_positional_args_rejected(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("positional" in e.lower() or "keyword" in e.lower() for e in errors)


# ── Unknown cadence kwargs ───────────────────────────────────────────

class TestUnknownCadenceKwargs:
    def test_single_unknown_kwarg(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(foo=BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("unknown" in e.lower() or "foo" in e for e in errors)

    def test_multiple_unknown_kwargs(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(foo=BarSize.DAILY, baz=ExecutionTiming.CLOSE_TO_CLOSE)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("foo" in e or "baz" in e for e in errors)

    def test_valid_plus_unknown_kwarg(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.DAILY, typo=BarSize.WEEKLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("typo" in e for e in errors)

    def test_misspelled_bar_size(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(barsize=BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("barsize" in e for e in errors)

    def test_misspelled_execution(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(exec=ExecutionTiming.CLOSE_TO_CLOSE)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("exec" in e for e in errors)


# ── Missing on_data ──────────────────────────────────────────────────

class TestMissingOnData:
    def test_no_on_data_method(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence()
""")
        assert any("on_data" in e for e in errors)

    def test_on_data_misspelled(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def ondata(self, data, portfolio):
        pass
""")
        assert any("on_data" in e for e in errors)

    def test_on_data_as_class_variable_not_method(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    on_data = None
""")
        assert any("on_data" in e for e in errors)

    def test_on_data_nested_in_other_method(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    def __init__(self):
        def on_data():
            pass
""")
        assert any("on_data" in e for e in errors)

    def test_on_data_as_lambda_not_detected(self):
        """on_data = lambda ... is an Assign, not a FunctionDef."""
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    on_data = lambda self, data, portfolio: None
""")
        assert any("on_data" in e for e in errors)


# ── Multiple errors accumulate ───────────────────────────────────────

class TestMultipleErrors:
    def test_bad_universe_and_missing_on_data(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = "AAPL"
""")
        assert len(errors) == 2
        assert any("list" in e for e in errors)
        assert any("on_data" in e for e in errors)

    def test_bad_universe_and_bad_cadence_and_missing_on_data(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = 42
    cadence = "daily"
""")
        assert len(errors) == 3

    def test_missing_universe_and_bad_cadence_and_missing_on_data(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    cadence = "daily"
""")
        assert len(errors) >= 2  # missing universe + bad cadence (+ missing on_data = 3)
        assert any("universe" in e.lower() or "missing" in e.lower() for e in errors)

    def test_bad_cadence_with_multiple_issues(self):
        """Invalid bar_size AND invalid execution should both be reported."""
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.HOURLY, execution=ExecutionTiming.FAKE)

    def on_data(self, data, portfolio):
        pass
""")
        assert any("bar_size" in e for e in errors)
        assert any("execution" in e for e in errors)

    def test_multiple_bad_tickers_all_reported(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["", "THISISSUPERLONGTICKER", "   "]

    def on_data(self, data, portfolio):
        pass
""")
        assert len([e for e in errors if "universe[" in e]) >= 2


# ── Edge cases ───────────────────────────────────────────────────────

class TestEdgeCases:
    def test_single_ticker_valid(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_unicode_in_source(self):
        errors = validate_strategy("""
# Strategy for 日本株
class MyStrategy(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_decorator_on_strategy_class(self):
        errors = validate_strategy("""
@some_decorator
class MyStrategy(Strategy):
    universe = ["SPY"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_strategy_with_docstring(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    \"\"\"A momentum strategy.\"\"\"
    universe = ["SPY", "IEF"]

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_strategy_with_init(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def __init__(self):
        super().__init__()
        self.lookback = 20

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []

    def test_strategy_with_complex_on_data_body(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY", "IEF"]

    def on_data(self, data, portfolio):
        spy = data["SPY"]
        if spy.close > spy.open:
            return TargetWeights({"SPY": 0.6, "IEF": 0.4})
        return Hold()
""")
        assert errors == []

    def test_whitespace_heavy_source(self):
        errors = validate_strategy("""


class MyStrategy(Strategy):

    universe = ["SPY"]


    def on_data(self, data, portfolio):

        pass

""")
        assert errors == []

    def test_only_whitespace_source(self):
        errors = validate_strategy("   \n\n  \n   ")
        assert any("No strategy class" in e for e in errors)

    def test_nested_class_not_confused(self):
        """Inner class shouldn't be validated as the strategy."""
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    class Inner:
        universe = 42  # should be ignored

    def on_data(self, data, portfolio):
        pass
""")
        assert errors == []