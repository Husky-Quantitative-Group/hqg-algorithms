"""validate.py"""
import ast
from typing import Optional


def validate_strategy(source: str) -> list[str]:
    """
    Validate strategy source code without executing it.
    Returns a list of error messages. Empty list = valid.
    """
    errors = []

    try:
        tree = ast.parse(source)
    except SyntaxError as e:
        return [f"Syntax error on line {e.lineno}: {e.msg}"]

    # Find first class with a universe assignment
    for node in ast.walk(tree):
        if not isinstance(node, ast.ClassDef):
            continue

        universe = _check_universe(node)
        cadence = _check_cadence(node)
        on_data = _check_on_data(node)

        if universe is not None:
            # This looks like a strategy class
            if universe:
                errors.extend(universe)
            if cadence:
                errors.extend(cadence)
            if on_data:
                errors.extend(on_data)
            return errors

    return ["No strategy class found. Define a class with 'universe' and 'on_data'."]


def _check_universe(cls: ast.ClassDef) -> Optional[list[str]]:
    """Returns None if no universe found, [] if valid, [errors] if invalid."""
    for item in cls.body:
        if not isinstance(item, ast.Assign):
            continue
        for target in item.targets:
            if isinstance(target, ast.Name) and target.id == "universe":
                try:
                    val = ast.literal_eval(item.value)
                except (ValueError, TypeError):
                    return [f"'universe' must be a list literal, e.g. [\"SPY\", \"IEF\"]"]
                if not isinstance(val, list):
                    return [f"'universe' must be a list, got {type(val).__name__}"]
                if not all(isinstance(s, str) for s in val):
                    return ["'universe' must contain only strings"]
                if len(val) == 0:
                    return ["'universe' must not be empty"]
                return []
    return None


def _check_cadence(cls: ast.ClassDef) -> Optional[list[str]]:
    """Returns None if no cadence found (ok, uses default), [] if valid, [errors] if invalid."""
    VALID_BAR_SIZES = {"DAILY", "WEEKLY", "MONTHLY", "QUARTERLY"}
    VALID_EXECUTIONS = {"CLOSE_TO_CLOSE", "CLOSE_TO_NEXT_OPEN", "OPEN_TO_OPEN"}

    for item in cls.body:
        if not isinstance(item, ast.Assign):
            continue
        for target in item.targets:
            if isinstance(target, ast.Name) and target.id == "cadence":
                node = item.value
                if not isinstance(node, ast.Call):
                    return ["'cadence' must be a Cadence(...) call"]

                func = node.func
                name = func.id if isinstance(func, ast.Name) else (func.attr if isinstance(func, ast.Attribute) else None)
                if name != "Cadence":
                    return [f"'cadence' must be a Cadence(...) call, got {name}(...)"]

                for kw in node.keywords:
                    val = kw.value
                    if not (isinstance(val, ast.Attribute) and isinstance(val.value, ast.Name)):
                        return [f"cadence argument '{kw.arg}' must be BarSize.X or ExecutionTiming.Y"]
                    if kw.arg == "bar_size" and val.attr not in VALID_BAR_SIZES:
                        return [f"Unknown bar_size '{val.attr}'. Valid: {', '.join(sorted(VALID_BAR_SIZES))}"]
                    if kw.arg == "execution" and val.attr not in VALID_EXECUTIONS:
                        return [f"Unknown execution '{val.attr}'. Valid: {', '.join(sorted(VALID_EXECUTIONS))}"]
                return []
    return None


def _check_on_data(cls: ast.ClassDef) -> Optional[list[str]]:
    """Returns None if not a strategy class, [] if valid, [errors] if missing."""
    for item in cls.body:
        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name == "on_data":
            return []
    return ["Missing 'on_data' method"]