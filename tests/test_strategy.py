"""test_strategy.py - verify Strategy class variable contract and logging."""

# usage: 
# pip install -e .
# pytest tests/ -v

import pytest
from hqg_algorithms import (
    Strategy, Cadence, BarSize, ExecutionTiming,
)


# ── Class variable contract ──────────────────────────────────────────

class TestStrategyClassVariables:
    def test_missing_universe_raises(self):
        with pytest.raises(TypeError, match="universe"):
            class BadStrategy(Strategy):
                cadence = Cadence()

                def on_data(self, data, portfolio):
                    pass

    def test_universe_not_a_list_raises(self):
        with pytest.raises(TypeError, match="universe"):
            class BadStrategy(Strategy):
                universe = "AAPL"

                def on_data(self, data, portfolio):
                    pass

    def test_cadence_defaults_when_omitted(self):
        class MinimalStrategy(Strategy):
            universe = ["AAPL"]

            def on_data(self, data, portfolio):
                pass

        assert MinimalStrategy.cadence == Cadence()
        assert MinimalStrategy.cadence.bar_size == BarSize.DAILY
        assert MinimalStrategy.cadence.execution == ExecutionTiming.CLOSE_TO_CLOSE

    def test_valid_strategy_definition(self):
        class GoodStrategy(Strategy):
            universe = ["SPY", "IEF", "GLD"]
            cadence = Cadence(bar_size=BarSize.WEEKLY, execution=ExecutionTiming.CLOSE_TO_NEXT_OPEN)

            def on_data(self, data, portfolio):
                pass

        assert GoodStrategy.universe == ["SPY", "IEF", "GLD"]
        assert GoodStrategy.cadence.bar_size == BarSize.WEEKLY

    def test_empty_universe_raises(self):
        with pytest.raises(TypeError, match="universe"):
            class BadStrategy(Strategy):
                universe = []

                def on_data(self, data, portfolio):
                    pass


# ── Logging ──────────────────────────────────────────────────────────

class TestStrategyLogging:
    def _make_strategy(self):
        class DummyStrategy(Strategy):
            universe = ["SPY"]

            def on_data(self, data, portfolio):
                pass

        return DummyStrategy()

    def test_default_log_handler_is_print(self, capsys):
        s = self._make_strategy()
        s.log("hello")
        assert capsys.readouterr().out.strip() == "hello"

    def test_override_log_handler_on_instance(self):
        s = self._make_strategy()
        captured = []
        s._log_handler = captured.append
        s.log("msg1")
        s.log("msg2")
        assert captured == ["msg1", "msg2"]

    def test_override_log_handler_on_class(self):
        captured = []

        class LoggingStrategy(Strategy):
            universe = ["SPY"]
            _log_handler = staticmethod(captured.append)

            def on_data(self, data, portfolio):
                pass

        a = LoggingStrategy()
        b = LoggingStrategy()
        a.log("from_a")
        b.log("from_b")
        assert captured == ["from_a", "from_b"]

    def test_instance_override_does_not_affect_other_instances(self, capsys):
        s1 = self._make_strategy()
        s2 = self._make_strategy()
        captured = []
        s1._log_handler = captured.append
        s2.log("to_print")
        s1.log("to_list")
        assert captured == ["to_list"]
        assert "to_print" in capsys.readouterr().out

    def test_log_handler_receives_exact_string(self):
        s = self._make_strategy()
        received = []
        s._log_handler = received.append
        msg = "  spaces & special chars! 🚀\n"
        s.log(msg)
        assert received == [msg]

    def test_override_with_lambda(self):
        s = self._make_strategy()
        results = []
        s._log_handler = lambda m: results.append(m.upper())
        s.log("hello")
        assert results == ["HELLO"]

    def test_subclass_override_does_not_affect_base_default(self):
        captured = []

        class CustomStrategy(Strategy):
            universe = ["SPY"]
            _log_handler = staticmethod(captured.append)

            def on_data(self, data, portfolio):
                pass

        class OtherStrategy(Strategy):
            universe = ["IEF"]

            def on_data(self, data, portfolio):
                pass

        assert OtherStrategy._log_handler is not CustomStrategy._log_handler
