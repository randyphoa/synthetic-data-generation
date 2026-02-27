"""Phase 3: Translate path constraints to Z3 and solve for concrete input values."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import z3

from synthetic_data.models.cfg_node import Parameter
from synthetic_data.models.condition import Constraint, Path

# Java type → Z3 sort constructor
_TYPE_MAP: dict[str, str] = {
    "int": "Int",
    "Integer": "Int",
    "long": "Int",
    "Long": "Int",
    "short": "Int",
    "Short": "Int",
    "byte": "Int",
    "Byte": "Int",
    "float": "Real",
    "Float": "Real",
    "double": "Real",
    "Double": "Real",
    "boolean": "Bool",
    "Boolean": "Bool",
    "char": "Int",  # 0–65535
    "Character": "Int",
    "String": "String",
}

# Java integer range limits
_INT_LIMITS: dict[str, tuple[int, int]] = {
    "byte": (-128, 127),
    "Byte": (-128, 127),
    "short": (-32768, 32767),
    "Short": (-32768, 32767),
    "int": (-2147483648, 2147483647),
    "Integer": (-2147483648, 2147483647),
    "long": (-9223372036854775808, 9223372036854775807),
    "Long": (-9223372036854775808, 9223372036854775807),
    "char": (0, 65535),
    "Character": (0, 65535),
}


@dataclass
class SolverResult:
    """Result of solving a path's constraints."""

    satisfiable: bool
    values: dict[str, Any]
    path_id: int


def solve_path(path: Path, parameters: list[Parameter]) -> SolverResult:
    """Solve a single path's constraint set using Z3.

    Returns a SolverResult indicating whether the path is satisfiable,
    and if so, the concrete values for each parameter.
    """
    # Separate z3-solvable vs llm-required constraints
    z3_constraints = [c for c in path.constraints if c.condition.solver == "z3"]
    llm_constraints = [c for c in path.constraints if c.condition.solver == "llm"]

    # If there are only LLM constraints (no Z3 work), return empty values
    # so llm_solver can fill them in
    if not z3_constraints and llm_constraints:
        return SolverResult(satisfiable=True, values={}, path_id=path.id)

    # Create Z3 variables for each parameter
    z3_vars = _create_z3_variables(parameters)

    solver = z3.Solver()

    # Add range constraints for bounded integer types
    for param in parameters:
        if param.java_type in _INT_LIMITS:
            lo, hi = _INT_LIMITS[param.java_type]
            var = z3_vars.get(param.name)
            if var is not None:
                solver.add(var >= lo)
                solver.add(var <= hi)

    # Translate and add each constraint
    for constraint in z3_constraints:
        z3_expr = _translate_constraint(constraint, z3_vars, parameters)
        if z3_expr is not None:
            solver.add(z3_expr)

    result = solver.check()

    if result == z3.sat:
        model = solver.model()
        values = _extract_values(model, z3_vars, parameters)
        return SolverResult(satisfiable=True, values=values, path_id=path.id)
    else:
        return SolverResult(satisfiable=False, values={}, path_id=path.id)


def solve_paths(
    paths: list[Path], parameters: list[Parameter]
) -> list[SolverResult]:
    """Solve all paths and return results. Marks unsatisfiable paths."""
    results = []
    for path in paths:
        result = solve_path(path, parameters)
        if not result.satisfiable:
            path.is_reachable = False
        results.append(result)
    return results


def _create_z3_variables(parameters: list[Parameter]) -> dict[str, Any]:
    """Create Z3 variables for each method parameter based on its Java type."""
    z3_vars: dict[str, Any] = {}
    for param in parameters:
        sort = _TYPE_MAP.get(param.java_type, "Int")
        if sort == "Int":
            z3_vars[param.name] = z3.Int(param.name)
        elif sort == "Real":
            z3_vars[param.name] = z3.Real(param.name)
        elif sort == "Bool":
            z3_vars[param.name] = z3.Bool(param.name)
        elif sort == "String":
            z3_vars[param.name] = z3.String(param.name)
        else:
            z3_vars[param.name] = z3.Int(param.name)
    return z3_vars


def _translate_constraint(
    constraint: Constraint,
    z3_vars: dict[str, Any],
    parameters: list[Parameter],
) -> Any | None:
    """Translate a single Constraint into a Z3 expression."""
    cond = constraint.condition
    negated = constraint.negated

    var = z3_vars.get(cond.variable)
    if var is None:
        # Variable might be a comparison between two parameters
        # or an unknown variable — skip
        return None

    param_types = {p.name: p.java_type for p in parameters}
    java_type = param_types.get(cond.variable, cond.java_type)
    z3_sort = _TYPE_MAP.get(java_type, "Int")

    expr = _make_comparison(var, cond.operator, cond.value, z3_sort, z3_vars)
    if expr is None:
        return None

    if negated:
        expr = z3.Not(expr)

    return expr


def _make_comparison(
    var: Any,
    operator: str,
    value: Any,
    z3_sort: str,
    z3_vars: dict[str, Any],
) -> Any | None:
    """Create a Z3 comparison expression."""
    # Value might be another variable name
    if isinstance(value, str) and value in z3_vars:
        rhs = z3_vars[value]
    else:
        rhs = _to_z3_value(value, z3_sort)

    if rhs is None:
        return None

    if operator == "<":
        return var < rhs
    elif operator == ">":
        return var > rhs
    elif operator == "<=":
        return var <= rhs
    elif operator == ">=":
        return var >= rhs
    elif operator == "==":
        return var == rhs
    elif operator == "!=":
        return var != rhs
    else:
        return None


def _to_z3_value(value: Any, z3_sort: str) -> Any | None:
    """Convert a Python value to the appropriate Z3 value."""
    if value is None:
        return None

    if z3_sort == "Int":
        if isinstance(value, bool):
            return z3.IntVal(1 if value else 0)
        if isinstance(value, (int, float)):
            return z3.IntVal(int(value))
        try:
            return z3.IntVal(int(value))
        except (ValueError, TypeError):
            return None

    elif z3_sort == "Real":
        if isinstance(value, (int, float)):
            return z3.RealVal(value)
        try:
            return z3.RealVal(float(value))
        except (ValueError, TypeError):
            return None

    elif z3_sort == "Bool":
        if isinstance(value, bool):
            return z3.BoolVal(value)
        if isinstance(value, str):
            return z3.BoolVal(value.lower() == "true")
        return z3.BoolVal(bool(value))

    elif z3_sort == "String":
        if isinstance(value, str):
            return z3.StringVal(value)
        return z3.StringVal(str(value))

    return None


def _extract_values(
    model: z3.ModelRef,
    z3_vars: dict[str, Any],
    parameters: list[Parameter],
) -> dict[str, Any]:
    """Extract concrete Python values from a Z3 model."""
    values: dict[str, Any] = {}
    param_types = {p.name: p.java_type for p in parameters}

    for name, var in z3_vars.items():
        val = model.eval(var, model_completion=True)
        java_type = param_types.get(name, "")
        values[name] = _z3_to_python(val, java_type)

    return values


def _z3_to_python(val: Any, java_type: str) -> Any:
    """Convert a Z3 value back to a Python value."""
    z3_sort = _TYPE_MAP.get(java_type, "Int")

    if z3_sort == "Bool":
        if z3.is_true(val):
            return True
        if z3.is_false(val):
            return False
        return bool(val)

    if z3_sort == "String":
        s = val.as_string()
        # Z3 wraps strings in quotes
        if s.startswith('"') and s.endswith('"'):
            return s[1:-1]
        return s

    if z3_sort == "Real":
        try:
            return float(val.as_decimal(10).rstrip("?"))
        except Exception:
            pass
        if z3.is_rational_value(val):
            num = val.numerator_as_long()
            den = val.denominator_as_long()
            try:
                return float(num) / float(den)
            except (OverflowError, ZeroDivisionError):
                # Extremely large rational — use Fraction for safe conversion
                from fractions import Fraction
                return float(Fraction(num, den))
        if z3.is_int_value(val):
            return float(val.as_long())
        return 0.0

    # Int sorts
    if z3.is_int_value(val):
        return val.as_long()
    try:
        return int(str(val))
    except (ValueError, TypeError):
        return 0
