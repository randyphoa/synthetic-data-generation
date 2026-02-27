"""Tests for Phase 3: LLM fallback solver."""

from unittest.mock import patch

from synthetic_data.models.cfg_node import MethodInfo, Parameter
from synthetic_data.models.condition import Condition, Constraint
from synthetic_data.solving.llm_solver import (
    solve_llm_constraints,
    _format_method_signature,
    _format_constraints,
)


def _make_constraint(variable, operator, value, java_type="String", solver="llm"):
    return Constraint(
        condition=Condition(
            variable=variable,
            operator=operator,
            value=value,
            java_type=java_type,
            source_expr=f'{variable}.{operator}("{value}")',
            solver=solver,
        ),
        negated=False,
    )


def _make_method_info():
    return MethodInfo(
        name="classify",
        parameters=[
            Parameter("age", "int"),
            Parameter("name", "String"),
        ],
        return_type="String",
    )


class TestFormatMethodSignature:
    def test_basic_signature(self):
        info = _make_method_info()
        sig = _format_method_signature(info)
        assert sig == "String classify(int age, String name)"

    def test_void_return(self):
        info = MethodInfo(
            name="process",
            parameters=[Parameter("x", "int")],
            return_type=None,
        )
        sig = _format_method_signature(info)
        assert sig == "void process(int x)"


class TestFormatConstraints:
    def test_with_z3_values(self):
        constraints = [_make_constraint("name", "startsWith", "Dr")]
        z3_values = {"age": 25}

        text = _format_constraints(constraints, z3_values)

        assert "age = 25" in text
        assert 'name.startsWith("Dr")' in text

    def test_without_z3_values(self):
        constraints = [_make_constraint("name", "startsWith", "Dr")]

        text = _format_constraints(constraints, {})

        assert "Already solved" not in text
        assert 'name.startsWith("Dr")' in text


class TestSolveLlmConstraints:
    @patch("synthetic_data.solving.llm_solver.call_llm_json")
    def test_merges_with_z3_values(self, mock_llm):
        mock_llm.return_value = {"name": "Dr. Smith"}

        constraints = [_make_constraint("name", "startsWith", "Dr")]
        z3_values = {"age": 25}
        method_info = _make_method_info()

        result = solve_llm_constraints(constraints, z3_values, method_info)

        assert result["age"] == 25       # Z3 value preserved
        assert result["name"] == "Dr. Smith"  # LLM value added

    @patch("synthetic_data.solving.llm_solver.call_llm_json")
    def test_z3_values_take_precedence(self, mock_llm):
        """If both Z3 and LLM solve the same variable, Z3 wins."""
        mock_llm.return_value = {"age": 30, "name": "Dr. Smith"}

        constraints = [_make_constraint("name", "startsWith", "Dr")]
        z3_values = {"age": 25}
        method_info = _make_method_info()

        result = solve_llm_constraints(constraints, z3_values, method_info)

        assert result["age"] == 25  # Z3 value, not LLM's 30

    @patch("synthetic_data.solving.llm_solver.call_llm_json")
    def test_empty_constraints_returns_z3_values(self, mock_llm):
        result = solve_llm_constraints([], {"age": 25}, _make_method_info())

        assert result == {"age": 25}
        mock_llm.assert_not_called()

    @patch("synthetic_data.solving.llm_solver.call_llm_json")
    def test_llm_failure_returns_z3_values(self, mock_llm):
        mock_llm.side_effect = Exception("LLM error")

        constraints = [_make_constraint("name", "startsWith", "Dr")]
        z3_values = {"age": 25}

        result = solve_llm_constraints(
            constraints, z3_values, _make_method_info(), max_retries=1
        )

        assert result == {"age": 25}

    @patch("synthetic_data.solving.llm_solver.call_llm_json")
    def test_non_dict_response_retries(self, mock_llm):
        """If LLM returns non-dict, it should retry."""
        mock_llm.side_effect = [
            ["not", "a", "dict"],       # bad response
            {"name": "Dr. Smith"},      # good response
        ]

        constraints = [_make_constraint("name", "startsWith", "Dr")]

        result = solve_llm_constraints(
            constraints, {}, _make_method_info(), max_retries=2
        )

        assert result["name"] == "Dr. Smith"
