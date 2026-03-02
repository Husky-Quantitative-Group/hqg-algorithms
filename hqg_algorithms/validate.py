"""validate.py"""
import ast
from typing import Optional

from hqg_algorithms.types import BarSize, ExecutionTiming

VALID_BAR_SIZES = {e.name for e in BarSize}
VALID_EXECUTIONS = {e.name for e in ExecutionTiming}
VALID_CADENCE_KWARGS = {"bar_size", "execution"}


def validate_strategy(source: str) -> list[str]:
    """
    Validate strategy source code without executing it.
    Returns a list of error messages. Empty list = valid.
    """
    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"Syntax error on line {e.lineno}: {e.msg}"]

    # Find strategy classes (classes that inherit from Strategy)
    strategy_classes = [
        node for node in ast.walk(tree)
        if isinstance(node, ast.ClassDef) and _is_strategy_subclass(node)
    ]

    if not strategy_classes:
        return ["No strategy class found. Define a class that inherits from Strategy with 'universe' and 'on_data'."]

    # Validate the first Strategy subclass
    cls = strategy_classes[0]
    errors = []

    universe_errors = _check_universe(cls)
    if universe_errors is None:
        errors.append(f"'{cls.name}' is missing 'universe'. Define it as a list of ticker strings, e.g. universe = [\"SPY\", \"IEF\"]")
    elif universe_errors:
        errors.extend(universe_errors)

    cadence_errors = _check_cadence(cls)
    if cadence_errors:
        errors.extend(cadence_errors)

    on_data_errors = _check_on_data(cls)
    if on_data_errors:
        errors.extend(on_data_errors)

    return errors


def _is_strategy_subclass(node: ast.ClassDef) -> bool:
    """Check if a class inherits from Strategy (handles `Strategy` and `mod.Strategy`)."""
    return any(
        (isinstance(b, ast.Name) and b.id == "Strategy")
        or (isinstance(b, ast.Attribute) and b.attr == "Strategy")
        for b in node.bases
    )


def _get_class_assign(cls: ast.ClassDef, name: str) -> Optional[ast.expr]:
    """Find value node for a class-level assignment by name. Supports Assign and AnnAssign."""
    for item in cls.body:
        if isinstance(item, ast.AnnAssign) and isinstance(item.target, ast.Name) and item.target.id == name:
            if item.value is None:
                return None  # annotation-only, no value
            return item.value
        if isinstance(item, ast.Assign):
            for target in item.targets:
                if isinstance(target, ast.Name) and target.id == name:
                    return item.value
    return None


MAX_TICKER_LEN = 12
MAX_UNIVERSE_SIZE = 200

def _check_universe(cls: ast.ClassDef) -> Optional[list[str]]:
    """Returns None if no universe found, [] if valid, [errors] if invalid."""
    value = _get_class_assign(cls, "universe")
    if value is None:
        return None

    try:
        val = ast.literal_eval(value)
    except (ValueError, TypeError):
        return ["'universe' must be a list literal, e.g. [\"SPY\", \"IEF\"]"]

    if not isinstance(val, list):
        return [f"'universe' must be a list, got {type(val).__name__}"]

    if len(val) == 0:
        return ["'universe' must not be empty"]

    errors = []
    seen = set()
    valid_count = 0

    for i, item in enumerate(val):
        if not isinstance(item, str):
            errors.append(f"universe[{i}]: expected string, got {type(item).__name__} ({item!r})")
            continue

        ticker = item.strip().upper()

        if not ticker:
            errors.append(f"universe[{i}]: empty or whitespace-only ticker")
        elif len(ticker) > MAX_TICKER_LEN:
            errors.append(f"universe[{i}]: '{ticker}' exceeds {MAX_TICKER_LEN} characters")
        elif ticker in seen:
            continue
        else:
            seen.add(ticker)
            valid_count += 1

    if valid_count <= 0:
        errors.append("'universe' has no valid tickers after cleaning")

    if valid_count > MAX_UNIVERSE_SIZE:
        errors.append(f"universe has {valid_count} distinct tickers (max {MAX_UNIVERSE_SIZE})")

    return errors


def _check_cadence(cls: ast.ClassDef) -> Optional[list[str]]:
    """Returns None if no cadence found (ok, uses default), [] if valid, [errors] if invalid."""
    value = _get_class_assign(cls, "cadence")
    if value is None:
        return None

    if not isinstance(value, ast.Call):
        return ["'cadence' must be a Cadence(...) call"]

    func = value.func
    name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
    if name != "Cadence":
        return [f"'cadence' must be a Cadence(...) call, got {name}(...)"]

    if value.args:
        return ["'cadence' does not accept positional arguments, use keyword arguments: Cadence(bar_size=..., execution=...)"]

    # Reject unknown kwargs
    unknown = {kw.arg for kw in value.keywords if kw.arg is not None} - VALID_CADENCE_KWARGS
    if unknown:
        return [f"Unknown cadence argument(s): {', '.join(sorted(unknown))}. Valid: {', '.join(sorted(VALID_CADENCE_KWARGS))}"]

    errors = []
    for kw in value.keywords:
        val = kw.value
        if not (isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name)):
            errors.append(f"cadence argument '{kw.arg}' must be BarSize.X or ExecutionTiming.Y")
            continue
        if kw.arg == "bar_size" and val.attr not in VALID_BAR_SIZES:
            errors.append(f"Unknown bar_size '{val.attr}'. Valid: {', '.join(sorted(VALID_BAR_SIZES))}")
        if kw.arg == "execution" and val.attr not in VALID_EXECUTIONS:
            errors.append(f"Unknown execution '{val.attr}'. Valid: {', '.join(sorted(VALID_EXECUTIONS))}")

    return errors


def _check_on_data(cls: ast.ClassDef) -> Optional[list[str]]:
    """Returns [] if valid, [errors] if missing or bad signature."""
    for item in cls.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "on_data":
            return []
    return ["Missing 'on_data' method"]