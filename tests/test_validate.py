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

    def test_addnl_class(self):
        errors = validate_strategy("""
class Helper:
    # universe = comment
    x = 10

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

    def test_extra_attributes_ignored(self):
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

    def test_class_without_universe_or_on_data(self):
        errors = validate_strategy("""
class Foo:
    x = 1
""")
        assert len(errors) == 1
        assert "No strategy class" in errors[0]

    def test_universe_in_method_not_detected(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    def __init__(self):
        self.universe = ["SPY"]
    def on_data(self, data, portfolio):
        pass
    """)
        assert "No strategy class" in errors[0]


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


# ── Bad universe ─────────────────────────────────────────────────────

class TestBadUniverse:
    def test_universe_is_string(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = "AAPL"

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "list" in errors[0]

    def test_universe_is_int(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = 42

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "list" in errors[0]

    def test_universe_has_non_string_elements(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["AAPL", 123]

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "strings" in errors[0]

    def test_universe_empty(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = []

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "empty" in errors[0]

    def test_universe_is_function_call(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = get_sp500()

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "list literal" in errors[0]

    def test_universe_is_variable(self):
        errors = validate_strategy("""
TICKERS = ["AAPL"]

class MyStrategy(Strategy):
    universe = TICKERS

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "list literal" in errors[0]

    def test_universe_is_concatenation(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["AAPL"] + ["MSFT"]

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "list literal" in errors[0]


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
        assert len(errors) == 1
        assert "Cadence(...)" in errors[0]

    def test_cadence_is_dict(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = {"bar_size": "1d"}

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "Cadence(...)" in errors[0]

    def test_cadence_wrong_function(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = NotCadence(bar_size=BarSize.DAILY)

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "Cadence(...)" in errors[0]

    def test_cadence_invalid_bar_size(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=BarSize.HOURLY)

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "bar_size" in errors[0]

    def test_cadence_invalid_execution(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(execution=ExecutionTiming.FAKE)

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "execution" in errors[0]

    def test_cadence_arg_is_variable(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size=my_var)

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "BarSize.X" in errors[0]

    def test_cadence_arg_is_string_literal(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence(bar_size="1d")

    def on_data(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "BarSize.X" in errors[0]


# ── Missing on_data ──────────────────────────────────────────────────

class TestMissingOnData:
    def test_no_on_data_method(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    cadence = Cadence()
""")
        assert len(errors) == 1
        assert "on_data" in errors[0]

    def test_on_data_misspelled(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]

    def ondata(self, data, portfolio):
        pass
""")
        assert len(errors) == 1
        assert "on_data" in errors[0]

    def test_on_data_nested_not_detected(self):
        errors = validate_strategy("""
class MyStrategy(Strategy):
    universe = ["SPY"]
    def __init__(self):
        def on_data():
            pass
""")
        assert any("on_data" in e for e in errors)


# ── Multiple errors ──────────────────────────────────────────────────

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
