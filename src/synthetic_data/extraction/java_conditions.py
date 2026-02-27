"""Phase 2a: Extract atomic conditions from compound boolean expressions in the AST."""

from __future__ import annotations

from synthetic_data.extraction.utility_method_map import UtilityMethodSpec, lookup
from synthetic_data.models.cfg_node import DecisionNode, Parameter
from synthetic_data.models.condition import (
    AndExpr,
    AtomicExpr,
    Condition,
    ConditionExpr,
    NotExpr,
    OrExpr,
)

Z3_OPERATORS = {"<", ">", "<=", ">=", "==", "!="}


def extract_conditions(
    decision_node: DecisionNode,
    parameters: list[Parameter],
) -> ConditionExpr:
    """Extract a structured condition expression tree from a decision node."""
    param_types = {p.name: p.java_type for p in parameters}
    ast = decision_node.condition_ast

    if ast is None:
        return AtomicExpr(
            Condition(
                variable="",
                operator="",
                value=None,
                java_type="",
                source_expr=decision_node.condition_expr,
                solver="llm",
            )
        )

    return _extract_expr(ast, param_types)


def classify_condition(condition: Condition) -> str:
    """Determine solver strategy: 'z3' or 'llm'."""
    if condition.operator in Z3_OPERATORS:
        return "z3"
    if condition.operator == "==" and isinstance(condition.value, bool):
        return "z3"
    return "llm"


def _extract_expr(node, param_types: dict[str, str]) -> ConditionExpr:
    text = node.text.decode()

    if node.type == "parenthesized_expression":
        named = [c for c in node.children if c.is_named]
        if named:
            return _extract_expr(named[0], param_types)

    if node.type == "binary_expression":
        op = _get_operator(node)
        left = node.child_by_field_name("left")
        right = node.child_by_field_name("right")

        if op == "&&":
            return AndExpr(
                left=_extract_expr(left, param_types),
                right=_extract_expr(right, param_types),
            )
        elif op == "||":
            return OrExpr(
                left=_extract_expr(left, param_types),
                right=_extract_expr(right, param_types),
            )
        else:
            return _make_comparison(left, op, right, param_types, text)

    if node.type == "unary_expression":
        op_text = node.children[0].text.decode()
        if op_text == "!":
            operand = node.children[1]
            return NotExpr(operand=_extract_expr(operand, param_types))

    if node.type == "identifier":
        name = text
        java_type = param_types.get(name, "boolean")
        return AtomicExpr(
            Condition(
                variable=name,
                operator="==",
                value=True,
                java_type=java_type,
                source_expr=name,
                solver="z3",
            )
        )

    if node.type in ("true", "false"):
        return AtomicExpr(
            Condition(
                variable="",
                operator="==",
                value=(text == "true"),
                java_type="boolean",
                source_expr=text,
                solver="z3",
            )
        )

    if node.type == "method_invocation":
        return _make_method_call(node, param_types)

    # Fallback: unrecognized expression → LLM-required
    return AtomicExpr(
        Condition(
            variable="",
            operator="",
            value=None,
            java_type="",
            source_expr=text,
            solver="llm",
        )
    )


def _get_operator(binary_node) -> str:
    left = binary_node.child_by_field_name("left")
    right = binary_node.child_by_field_name("right")
    for child in binary_node.children:
        if child.id != left.id and child.id != right.id and not child.is_named:
            return child.type
    return ""


def _make_comparison(left, op, right, param_types, full_text) -> AtomicExpr:
    left_text = left.text.decode()
    right_text = right.text.decode()

    variable = None
    value = None
    java_type = None
    actual_op = op

    # Check if either side is a getter on a known parameter (Enhancement 3)
    left_flat = _resolve_getter_to_flat_param(left, param_types) if left.type == "method_invocation" else None
    right_flat = _resolve_getter_to_flat_param(right, param_types) if right.type == "method_invocation" else None

    left_name = left_flat or left_text
    right_name = right_flat or right_text

    if left_name in param_types:
        variable = left_name
        java_type = param_types[left_name]
        value = _parse_literal(right_name, java_type)
    elif right_name in param_types:
        variable = right_name
        java_type = param_types[right_name]
        value = _parse_literal(left_name, java_type)
        actual_op = _flip_operator(op)
    else:
        # Neither side is a known parameter — keep as-is
        variable = left_name
        value = right_name
        java_type = _guess_type(right_name)

    solver = "z3" if op in Z3_OPERATORS else "llm"

    return AtomicExpr(
        Condition(
            variable=variable,
            operator=actual_op,
            value=value,
            java_type=java_type or "",
            source_expr=full_text,
            solver=solver,
        )
    )


def _make_method_call(node, param_types) -> AtomicExpr:
    text = node.text.decode()
    obj = node.child_by_field_name("object")
    name = node.child_by_field_name("name")

    class_name = obj.text.decode() if obj else ""
    method_name = name.text.decode() if name else ""

    # Enhancement 1: Try utility method registry
    spec = lookup(class_name, method_name)
    if spec is not None:
        result = _resolve_utility_method(spec, node, param_types, text)
        if result is not None:
            return result

    # Fallback: opaque method call → LLM
    java_type = param_types.get(class_name, "")
    return AtomicExpr(
        Condition(
            variable=class_name,
            operator=method_name,
            value=None,
            java_type=java_type,
            source_expr=text,
            solver="llm",
        )
    )


def _extract_arguments(node) -> list:
    """Extract argument nodes from a method_invocation's argument_list."""
    args_node = node.child_by_field_name("arguments")
    if args_node is None:
        return []
    return [c for c in args_node.children if c.is_named]


def _resolve_argument_name(arg_node, param_types: dict[str, str], type_hint: str = "") -> str:
    """Resolve an argument node to a parameter name.

    Handles plain identifiers, field access, and getter calls (Enhancement 3).
    If the argument is a getter on a known parameter, registers the flattened
    name in param_types and returns it.
    """
    if arg_node.type == "identifier":
        return arg_node.text.decode()

    if arg_node.type == "field_access":
        return arg_node.text.decode()

    if arg_node.type == "method_invocation":
        flat = _resolve_getter_to_flat_param(arg_node, param_types, type_hint)
        if flat is not None:
            return flat

    return arg_node.text.decode()


def _resolve_getter_to_flat_param(
    method_node, param_types: dict[str, str], type_hint: str = ""
) -> str | None:
    """Detect paramName.getXxx() and return flattened name paramName__fieldName.

    If the object is a known parameter and the method looks like a getter
    (name starts with 'get', no arguments), return the flattened name and
    register it in param_types with the appropriate type.
    """
    obj = method_node.child_by_field_name("object")
    name = method_node.child_by_field_name("name")
    if obj is None or name is None:
        return None

    obj_text = obj.text.decode()
    method_name = name.text.decode()

    # Object must be a known parameter
    if obj_text not in param_types:
        return None

    # Must be a getter (starts with "get" and no arguments)
    if not method_name.startswith("get"):
        return None

    args = _extract_arguments(method_node)
    if args:
        return None

    # Derive the field name from the getter: getComdteC → comdteC
    field_name = method_name[3:]
    if field_name:
        field_name = field_name[0].lower() + field_name[1:]

    flat_name = f"{obj_text}__{field_name}"

    # Register in param_types if not already present
    if flat_name not in param_types:
        # Use type hint from utility spec if available, else guess from obj type
        inferred_type = type_hint or ""
        param_types[flat_name] = inferred_type

    return flat_name


def _resolve_utility_method(
    spec: UtilityMethodSpec, node, param_types: dict[str, str], text: str
) -> AtomicExpr | None:
    """Resolve a utility method call to an AtomicExpr using the spec."""
    args = _extract_arguments(node)

    if spec.arg_count == 1 and len(args) == 1:
        variable = _resolve_argument_name(args[0], param_types, spec.result_type)
        java_type = param_types.get(variable, spec.result_type)
        if spec.result_type and not param_types.get(variable):
            param_types[variable] = spec.result_type
        return AtomicExpr(
            Condition(
                variable=variable,
                operator=spec.operator,
                value=spec.default_value,
                java_type=java_type or spec.result_type,
                source_expr=text,
                solver="z3",
            )
        )

    if spec.arg_count == 2 and len(args) == 2:
        arg0_name = _resolve_argument_name(args[0], param_types, spec.result_type)
        arg1_name = _resolve_argument_name(args[1], param_types, spec.result_type)

        arg0_is_param = arg0_name in param_types
        arg1_is_param = arg1_name in param_types

        if arg0_is_param and not arg1_is_param:
            # Normal: variable is first arg, value is second
            variable = arg0_name
            value = _parse_literal(arg1_name, param_types.get(arg0_name, spec.result_type))
            java_type = param_types.get(arg0_name, spec.result_type)
            operator = spec.operator
        elif arg1_is_param and not arg0_is_param:
            # Flipped: variable is second arg, value is first
            variable = arg1_name
            value = _parse_literal(arg0_name, param_types.get(arg1_name, spec.result_type))
            java_type = param_types.get(arg1_name, spec.result_type)
            operator = _flip_operator(spec.operator)
        elif arg0_is_param and arg1_is_param:
            # Both are params: keep first as variable, second as value (by name)
            variable = arg0_name
            value = arg1_name
            java_type = param_types.get(arg0_name, spec.result_type)
            operator = spec.operator
        else:
            # Neither is a known param — pick first as variable
            variable = arg0_name
            value = _parse_literal(arg1_name, spec.result_type)
            java_type = spec.result_type
            operator = spec.operator

        return AtomicExpr(
            Condition(
                variable=variable,
                operator=operator,
                value=value,
                java_type=java_type or spec.result_type,
                source_expr=text,
                solver="z3",
            )
        )

    return None


def _parse_literal(text: str, java_type: str):
    """Parse a Java literal into a Python value."""
    text = text.strip()
    if java_type in ("int", "Integer", "long", "Long"):
        text = text.rstrip("lL")
        try:
            return int(text)
        except ValueError:
            return text
    elif java_type in ("float", "Float", "double", "Double"):
        text = text.rstrip("fFdD")
        try:
            return float(text)
        except ValueError:
            return text
    elif java_type in ("boolean", "Boolean"):
        if text == "true":
            return True
        elif text == "false":
            return False
        return text
    elif java_type == "String":
        if text.startswith('"') and text.endswith('"'):
            return text[1:-1]
        return text
    # Auto-detect
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]
    if text == "null":
        return None
    if text == "true":
        return True
    if text == "false":
        return False
    try:
        return int(text)
    except ValueError:
        pass
    try:
        return float(text)
    except ValueError:
        return text


def _flip_operator(op: str) -> str:
    return {">": "<", "<": ">", ">=": "<=", "<=": ">=", "==": "==", "!=": "!="}.get(
        op, op
    )


def _guess_type(text: str) -> str:
    if text.startswith('"'):
        return "String"
    if text in ("true", "false"):
        return "boolean"
    if text == "null":
        return ""
    if "." in text:
        return "double"
    try:
        int(text)
        return "int"
    except ValueError:
        return ""
