"""Tests for Phase 3: Z3 constraint solving."""

from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.models.cfg_node import Parameter
from synthetic_data.models.condition import Condition, Constraint, Path
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import extract_methods, parse_file
from synthetic_data.solving.z3_solver import SolverResult, solve_path, solve_paths


def _make_condition(variable, operator, value, java_type="int", solver="z3"):
    return Condition(
        variable=variable,
        operator=operator,
        value=value,
        java_type=java_type,
        source_expr=f"{variable} {operator} {value}",
        solver=solver,
    )


def _make_path(path_id, constraints, leaf_value="result"):
    return Path(
        id=path_id,
        constraints=constraints,
        leaf_type="return",
        leaf_value=leaf_value,
    )


# --- Basic constraint solving ---


class TestSolvePathBasic:
    def test_simple_less_than(self):
        params = [Parameter("age", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("age", "<", 18), negated=False)]
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["age"] < 18

    def test_simple_greater_than(self):
        params = [Parameter("age", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("age", ">", 65), negated=False)]
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["age"] > 65

    def test_equality(self):
        params = [Parameter("x", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("x", "==", 42), negated=False)]
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["x"] == 42

    def test_negated_constraint(self):
        """NOT(age < 18) means age >= 18."""
        params = [Parameter("age", "int")]
        path = _make_path(
            1, [Constraint(_make_condition("age", "<", 18), negated=True)]
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["age"] >= 18

    def test_contradictory_constraints_unsat(self):
        """age < 10 AND age > 20 is unsatisfiable."""
        params = [Parameter("age", "int")]
        path = _make_path(
            1,
            [
                Constraint(_make_condition("age", "<", 10), negated=False),
                Constraint(_make_condition("age", ">", 20), negated=False),
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is False
        assert result.values == {}


# --- Multiple parameters ---


class TestSolvePathMultiParam:
    def test_two_params(self):
        params = [Parameter("age", "int"), Parameter("income", "double")]
        path = _make_path(
            1,
            [
                Constraint(_make_condition("age", ">=", 18), negated=False),
                Constraint(
                    _make_condition("income", ">", 50000, java_type="double"),
                    negated=False,
                ),
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["age"] >= 18
        assert result.values["income"] > 50000

    def test_boolean_param(self):
        params = [Parameter("isMember", "boolean")]
        path = _make_path(
            1,
            [
                Constraint(
                    _make_condition("isMember", "==", True, java_type="boolean"),
                    negated=False,
                )
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["isMember"] is True

    def test_boolean_negated(self):
        """NOT(isMember == true) means isMember is false."""
        params = [Parameter("isMember", "boolean")]
        path = _make_path(
            1,
            [
                Constraint(
                    _make_condition("isMember", "==", True, java_type="boolean"),
                    negated=True,
                )
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["isMember"] is False


# --- Type handling ---


class TestTypeHandling:
    def test_double_type(self):
        params = [Parameter("price", "double")]
        path = _make_path(
            1,
            [
                Constraint(
                    _make_condition("price", ">", 99.99, java_type="double"),
                    negated=False,
                )
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert isinstance(result.values["price"], float)
        assert result.values["price"] > 99.99

    def test_long_type(self):
        params = [Parameter("bigNum", "long")]
        path = _make_path(
            1,
            [
                Constraint(
                    _make_condition("bigNum", ">", 2147483647, java_type="long"),
                    negated=False,
                )
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["bigNum"] > 2147483647


# --- LLM-only paths ---


class TestLLMOnlyPath:
    def test_all_llm_constraints_returns_empty_values(self):
        params = [Parameter("name", "String")]
        path = _make_path(
            1,
            [
                Constraint(
                    _make_condition(
                        "name", "startsWith", "Dr", java_type="String", solver="llm"
                    ),
                    negated=False,
                )
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values == {}

    def test_mixed_z3_and_llm(self):
        """Z3 solves what it can, LLM constraints are skipped."""
        params = [
            Parameter("age", "int"),
            Parameter("name", "String"),
        ]
        path = _make_path(
            1,
            [
                Constraint(_make_condition("age", ">", 18), negated=False),
                Constraint(
                    _make_condition(
                        "name", "startsWith", "Dr", java_type="String", solver="llm"
                    ),
                    negated=False,
                ),
            ],
        )

        result = solve_path(path, params)

        assert result.satisfiable is True
        assert result.values["age"] > 18
        # name is filled by Z3 with a default (since it's in params but
        # no Z3 constraint), LLM solver would override later
        assert "name" in result.values


# --- Integration with CustomerClassifier ---


class TestCustomerClassifierSolving:
    def test_solve_all_paths(self, customer_classifier_path):
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        results = solve_paths(paths, params)

        assert len(results) == len(paths)

        # At least the 6 meaningful paths should be satisfiable
        sat_results = [r for r in results if r.satisfiable]
        assert len(sat_results) >= 6

    def test_junior_path_values(self, customer_classifier_path):
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        junior = next(p for p in paths if p.leaf_value == '"junior"')
        result = solve_path(junior, params)

        assert result.satisfiable is True
        assert result.values["age"] < 18

    def test_premium_path_values(self, customer_classifier_path):
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        premium = next(p for p in paths if p.leaf_value == '"premium"')
        result = solve_path(premium, params)

        assert result.satisfiable is True
        assert result.values["age"] >= 18
        assert result.values["age"] < 65
        assert result.values["income"] > 50000
        assert result.values["isMember"] is True

    def test_senior_member_path_values(self, customer_classifier_path):
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        senior_member = next(
            p for p in paths if p.leaf_value == '"senior_member"'
        )
        result = solve_path(senior_member, params)

        assert result.satisfiable is True
        assert result.values["age"] >= 65
        assert result.values["isMember"] is True

    def test_dead_paths_detected(self, customer_classifier_path):
        """DNF expansion creates 2 contradictory paths that should be unsat."""
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        results = solve_paths(paths, params)
        unsat = [r for r in results if not r.satisfiable]

        assert len(unsat) == 2

    def test_solve_paths_marks_unreachable(self, customer_classifier_path):
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        solve_paths(paths, params)

        unreachable = [p for p in paths if not p.is_reachable]
        assert len(unreachable) == 2
