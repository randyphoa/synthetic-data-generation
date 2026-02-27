"""Tests for Phase 3b: Boundary value and edge case generation."""

from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.models.cfg_node import Parameter
from synthetic_data.models.condition import Condition, Constraint, Path
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import extract_methods, parse_file
from synthetic_data.solving.boundary import (
    DataRow,
    generate_boundary_rows,
    generate_edge_case_rows,
)
from synthetic_data.solving.z3_solver import solve_paths


def _make_condition(variable, operator, value, java_type="int"):
    return Condition(
        variable=variable,
        operator=operator,
        value=value,
        java_type=java_type,
        source_expr=f"{variable} {operator} {value}",
        solver="z3",
    )


def _make_path(path_id, constraints, leaf_value="result"):
    return Path(
        id=path_id,
        constraints=constraints,
        leaf_type="return",
        leaf_value=leaf_value,
    )


# --- Boundary value generation ---


class TestBoundaryRows:
    def test_less_than_boundary(self):
        """x < 18 should produce x=17 (last passing). x=18 fails the
        constraint so Z3 correctly rejects it for this path."""
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", "<", 18), negated=False)]
        )

        rows = generate_boundary_rows([path], params)

        values = {r.values["x"] for r in rows}
        assert 17 in values  # last passing

    def test_less_than_boundary_across_paths(self):
        """Across two paths (x<18 and NOT x<18), both boundary values appear."""
        params = [Parameter("x", "int")]
        path1 = _make_path(
            1, [Constraint(_make_condition("x", "<", 18), negated=False)]
        )
        path2 = _make_path(
            2, [Constraint(_make_condition("x", "<", 18), negated=True)]
        )

        rows = generate_boundary_rows([path1, path2], params)

        values = {r.values["x"] for r in rows}
        assert 17 in values  # satisfies x < 18
        assert 18 in values  # satisfies NOT(x < 18)

    def test_greater_equal_boundary(self):
        """x >= 65: x=65 passes, x=64 fails (rejected for this path)."""
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", ">=", 65), negated=False)]
        )

        rows = generate_boundary_rows([path], params)

        values = {r.values["x"] for r in rows}
        assert 65 in values  # first passing

    def test_equality_boundary(self):
        """x == 100: only x=100 satisfies the constraint on this path."""
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", "==", 100), negated=False)]
        )

        rows = generate_boundary_rows([path], params)

        values = {r.values["x"] for r in rows}
        assert 100 in values

    def test_not_equal_boundary(self):
        """x != 0: x=-1, x=1 pass; x=0 fails the constraint."""
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", "!=", 0), negated=False)]
        )

        rows = generate_boundary_rows([path], params)

        values = {r.values["x"] for r in rows}
        assert -1 in values
        assert 1 in values

    def test_double_boundary(self):
        """income > 50000.0 should produce at least one boundary value."""
        params = [Parameter("income", "double")]
        path = _make_path(
            1,
            [
                Constraint(
                    _make_condition("income", ">", 50000.0, java_type="double"),
                    negated=False,
                )
            ],
        )

        rows = generate_boundary_rows([path], params)

        assert len(rows) >= 1
        assert all(r.row_type == "boundary" for r in rows)

    def test_unreachable_path_skipped(self):
        """Unreachable paths should not generate boundary rows."""
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", "<", 18), negated=False)]
        )
        path.is_reachable = False

        rows = generate_boundary_rows([path], params)

        assert len(rows) == 0

    def test_boundary_row_metadata(self):
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", "<", 18), negated=False)]
        )

        rows = generate_boundary_rows([path], params)

        for row in rows:
            assert row.row_type == "boundary"
            assert row.path_id == 1
            assert "boundary" in row.source

    def test_deduplication(self):
        """Same boundary value from multiple constraints shouldn't duplicate."""
        params = [Parameter("x", "int")]
        path = _make_path(
            1,
            [
                Constraint(_make_condition("x", ">=", 18), negated=False),
                Constraint(_make_condition("x", "<", 65), negated=False),
            ],
        )

        rows = generate_boundary_rows([path], params)
        value_keys = [(r.path_id, tuple(sorted(r.values.items()))) for r in rows]

        assert len(value_keys) == len(set(value_keys))


# --- Edge case generation ---


class TestEdgeCaseRows:
    def test_int_edge_cases(self):
        """Int parameters should get 0, -1, MIN_VALUE, MAX_VALUE."""
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", ">", -9999999), negated=False)]
        )

        rows = generate_edge_case_rows([path], params)

        values = {r.values["x"] for r in rows}
        # 0 and -1 should be > -9999999, so they're included
        assert 0 in values
        assert -1 in values

    def test_boolean_edge_cases(self):
        """Boolean parameters should get True and False."""
        params = [Parameter("flag", "boolean")]
        # No numeric constraint — just a boolean equality
        path = _make_path(
            1,
            [
                Constraint(
                    _make_condition("flag", "==", True, java_type="boolean"),
                    negated=False,
                )
            ],
        )

        rows = generate_edge_case_rows([path], params)

        # Only True should satisfy flag == True
        assert len(rows) >= 1
        assert all(r.values["flag"] is True for r in rows)

    def test_edge_case_metadata(self):
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", ">", -9999999), negated=False)]
        )

        rows = generate_edge_case_rows([path], params)

        for row in rows:
            assert row.row_type == "edge_case"
            assert "edge_case" in row.source

    def test_unreachable_path_skipped(self):
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", "<", 18), negated=False)]
        )
        path.is_reachable = False

        rows = generate_edge_case_rows([path], params)

        assert len(rows) == 0


# --- Integration with CustomerClassifier ---


class TestCustomerClassifierBoundary:
    def test_boundary_rows_generated(self, customer_classifier_path):
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        # Mark dead paths
        solve_paths(paths, params)

        rows = generate_boundary_rows(paths, params)

        assert len(rows) > 0
        assert all(isinstance(r, DataRow) for r in rows)
        assert all(r.row_type == "boundary" for r in rows)

    def test_boundary_covers_key_values(self, customer_classifier_path):
        """Should include boundary values for age=17,18,64,65 and income=50000."""
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        solve_paths(paths, params)
        rows = generate_boundary_rows(paths, params)

        age_values = {r.values["age"] for r in rows}
        income_values = {r.values["income"] for r in rows}

        # Key age boundaries
        assert 17 in age_values   # boundary for age < 18
        assert 18 in age_values   # boundary for age < 18
        assert 64 in age_values   # boundary for age >= 65
        assert 65 in age_values   # boundary for age >= 65

        # Key income boundaries
        assert any(v == 50001.0 or v == 50000.0 for v in income_values)

    def test_edge_case_rows_generated(self, customer_classifier_path):
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        solve_paths(paths, params)
        rows = generate_edge_case_rows(paths, params)

        assert len(rows) > 0
        assert all(r.row_type == "edge_case" for r in rows)
