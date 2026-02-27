"""Phase 3b: Generate boundary value and edge case rows for each condition."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import z3

from synthetic_data.models.cfg_node import Parameter
from synthetic_data.models.condition import Condition, Constraint, Path
from synthetic_data.solving.z3_solver import (
    SolverResult,
    _INT_LIMITS,
    _TYPE_MAP,
    _create_z3_variables,
    _extract_values,
)


@dataclass
class DataRow:
    """A generated data row with metadata."""

    values: dict[str, Any]
    path_id: int
    row_type: str  # "path", "boundary", "edge_case"
    source: str  # description of what generated this row


# ---------------------------------------------------------------------------
# Boundary values per comparison operator
# ---------------------------------------------------------------------------

_BOUNDARY_MAP: dict[str, list[int]] = {
    # operator → offsets from the comparison value
    "<": [-1, 0],       # last passing, first failing
    "<=": [0, 1],       # last passing, first failing
    ">": [1, 0],        # first passing, last failing
    ">=": [0, -1],      # first passing, last failing
    "==": [-1, 0, 1],   # below, at, above
    "!=": [-1, 0, 1],   # below, at, above
}

# ---------------------------------------------------------------------------
# Edge case values per Java type
# ---------------------------------------------------------------------------

_EDGE_VALUES: dict[str, list[Any]] = {
    "int": [0, -1, -2147483648, 2147483647],
    "Integer": [0, -1, -2147483648, 2147483647],
    "long": [0, -1, -9223372036854775808, 9223372036854775807],
    "Long": [0, -1, -9223372036854775808, 9223372036854775807],
    "short": [0, -1, -32768, 32767],
    "Short": [0, -1, -32768, 32767],
    "byte": [0, -1, -128, 127],
    "Byte": [0, -1, -128, 127],
    "float": [0.0, -0.0, 1.17549435e-38, 3.4028235e+38],
    "Float": [0.0, -0.0, 1.17549435e-38, 3.4028235e+38],
    "double": [0.0, -0.0, 5e-324, 1.7976931348623157e+308],
    "Double": [0.0, -0.0, 5e-324, 1.7976931348623157e+308],
    "boolean": [True, False],
    "Boolean": [True, False],
    "char": [0, 32, 65535],       # '\0', ' ', Character.MAX_VALUE
    "Character": [0, 32, 65535],
    "String": ["", None],
}


def generate_boundary_rows(
    paths: list[Path],
    parameters: list[Parameter],
) -> list[DataRow]:
    """Generate boundary value rows for numeric comparison conditions.

    For each path and each comparison condition on that path, pins the
    variable to each boundary value and solves the remaining variables
    with Z3. Skips if the boundary makes the path unsatisfiable.
    """
    rows: list[DataRow] = []

    for path in paths:
        if not path.is_reachable:
            continue

        for constraint in path.constraints:
            cond = constraint.condition
            if cond.solver != "z3":
                continue
            if cond.operator not in _BOUNDARY_MAP:
                continue
            if not isinstance(cond.value, (int, float)):
                continue

            offsets = _BOUNDARY_MAP[cond.operator]
            for offset in offsets:
                boundary_val = cond.value + offset
                row = _solve_with_pin(
                    path, parameters, cond.variable, boundary_val
                )
                if row is not None:
                    desc = (
                        f"boundary: {cond.variable} = {boundary_val} "
                        f"(from {cond.source_expr})"
                    )
                    rows.append(
                        DataRow(
                            values=row,
                            path_id=path.id,
                            row_type="boundary",
                            source=desc,
                        )
                    )

    return _deduplicate(rows)


def generate_edge_case_rows(
    paths: list[Path],
    parameters: list[Parameter],
) -> list[DataRow]:
    """Generate edge case rows by injecting type-specific extreme values.

    For each parameter, tries each edge value for its type.  Pins the
    parameter to the edge value and solves the remaining variables with Z3.
    Skips if the edge value is incompatible with the path's constraints.
    """
    rows: list[DataRow] = []

    for path in paths:
        if not path.is_reachable:
            continue

        for param in parameters:
            edge_vals = _EDGE_VALUES.get(param.java_type, [])
            for edge_val in edge_vals:
                if edge_val is None:
                    # Can't pin null in Z3 — skip
                    continue

                row = _solve_with_pin(
                    path, parameters, param.name, edge_val
                )
                if row is not None:
                    desc = (
                        f"edge_case: {param.name} = {edge_val!r} "
                        f"({param.java_type})"
                    )
                    rows.append(
                        DataRow(
                            values=row,
                            path_id=path.id,
                            row_type="edge_case",
                            source=desc,
                        )
                    )

    return _deduplicate(rows)


def _solve_with_pin(
    path: Path,
    parameters: list[Parameter],
    pin_variable: str,
    pin_value: Any,
) -> dict[str, Any] | None:
    """Solve a path's constraints with one variable pinned to a specific value.

    Returns the concrete values dict if satisfiable, or None.
    """
    z3_vars = _create_z3_variables(parameters)
    solver = z3.Solver()

    # Add range constraints for bounded types
    for param in parameters:
        if param.java_type in _INT_LIMITS:
            lo, hi = _INT_LIMITS[param.java_type]
            var = z3_vars.get(param.name)
            if var is not None:
                solver.add(var >= lo)
                solver.add(var <= hi)

    # Pin the target variable
    pin_var = z3_vars.get(pin_variable)
    if pin_var is None:
        return None

    pin_z3 = _python_to_z3(pin_value, pin_variable, parameters)
    if pin_z3 is None:
        return None
    solver.add(pin_var == pin_z3)

    # Add all z3-solvable constraints
    for constraint in path.constraints:
        cond = constraint.condition
        if cond.solver != "z3":
            continue

        var = z3_vars.get(cond.variable)
        if var is None:
            continue

        # Determine rhs
        if isinstance(cond.value, str) and cond.value in z3_vars:
            rhs = z3_vars[cond.value]
        else:
            rhs = _python_to_z3(cond.value, cond.variable, parameters)
            if rhs is None:
                continue

        expr = _make_cmp(var, cond.operator, rhs)
        if expr is None:
            continue

        if constraint.negated:
            expr = z3.Not(expr)
        solver.add(expr)

    if solver.check() == z3.sat:
        model = solver.model()
        return _extract_values(model, z3_vars, parameters)

    return None


def _python_to_z3(value: Any, var_name: str, parameters: list[Parameter]) -> Any:
    """Convert a Python value to the appropriate Z3 literal."""
    param_type = next(
        (p.java_type for p in parameters if p.name == var_name), ""
    )
    z3_sort = _TYPE_MAP.get(param_type, "Int")

    if z3_sort == "Bool":
        return z3.BoolVal(bool(value))
    elif z3_sort == "Real":
        try:
            return z3.RealVal(float(value))
        except (ValueError, TypeError):
            return None
    elif z3_sort == "String":
        return z3.StringVal(str(value))
    else:
        try:
            return z3.IntVal(int(value))
        except (ValueError, TypeError):
            return None


def _make_cmp(var: Any, operator: str, rhs: Any) -> Any:
    """Create a Z3 comparison expression."""
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
    return None


def _deduplicate(rows: list[DataRow]) -> list[DataRow]:
    """Remove rows with identical (path_id, values) combinations."""
    seen: set[tuple] = set()
    unique: list[DataRow] = []
    for row in rows:
        key = (row.path_id, tuple(sorted(row.values.items())))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique
