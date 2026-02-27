"""Build a same-class call graph by walking method ASTs for method_invocation nodes."""

from __future__ import annotations

from synthetic_data.models.call_graph import CallGraph, CallSite
from synthetic_data.models.cfg_node import MethodInfo


def build_call_graph(
    methods: list[MethodInfo],
    source: bytes,
    class_name: str | None = None,
) -> CallGraph:
    """Build a same-class call graph from extracted methods.

    Walks each method's AST looking for method_invocation nodes whose
    receiver is absent (implicit this) or ``this.``. For each such call,
    checks whether the target method exists in the class and records a
    CallSite.
    """
    method_names = {m.name for m in methods}
    edges: list[CallSite] = []
    adjacency: dict[str, list[CallSite]] = {m.name: [] for m in methods}

    for method in methods:
        if method.node is None:
            continue
        _walk_for_calls(
            method.node, source, method.name, method_names, edges, adjacency
        )

    return CallGraph(
        class_name=class_name or "",
        methods=[m.name for m in methods],
        edges=edges,
        adjacency=adjacency,
    )


def _walk_for_calls(
    node,
    source: bytes,
    caller_name: str,
    method_names: set[str],
    edges: list[CallSite],
    adjacency: dict[str, list[CallSite]],
):
    """Recursively walk AST to find method_invocation nodes."""
    if node.type == "method_invocation":
        call_site = _try_parse_call(node, source, caller_name, method_names)
        if call_site is not None:
            edges.append(call_site)
            adjacency[caller_name].append(call_site)
        # Don't return — still walk children for nested invocations

    for child in node.children:
        _walk_for_calls(child, source, caller_name, method_names, edges, adjacency)


def _try_parse_call(
    invocation_node,
    source: bytes,
    caller_name: str,
    method_names: set[str],
) -> CallSite | None:
    """Try to parse a method_invocation as a same-class call.

    Returns a CallSite if the call target is a same-class method.
    """
    obj_node = invocation_node.child_by_field_name("object")
    name_node = invocation_node.child_by_field_name("name")

    if name_node is None:
        return None

    callee_name = _text(name_node, source)

    # Only include same-class calls: no receiver or `this` receiver
    if obj_node is not None:
        receiver = _text(obj_node, source)
        if receiver != "this":
            return None

    if callee_name not in method_names:
        return None

    # Don't record self-recursive calls
    if callee_name == caller_name:
        return None

    # Detect result assignment by walking up the parent chain
    result_variable = _detect_result_variable(invocation_node, source)

    return CallSite(
        caller_method=caller_name,
        callee_method=callee_name,
        call_node=invocation_node,
        result_variable=result_variable,
        is_same_class=True,
    )


def _detect_result_variable(invocation_node, source: bytes) -> str | None:
    """Check if the method call result is assigned to a variable.

    Handles:
    - ``boolean isValid = validate();``  (local_variable_declaration)
    - ``isValid = validate();``  (assignment_expression)
    """
    parent = invocation_node.parent
    if parent is None:
        return None

    # Case: assignment_expression  (e.g., isValid = validate())
    if parent.type == "assignment_expression":
        left = parent.child_by_field_name("left")
        if left is not None:
            return _text(left, source)

    # Case: variable_declarator inside local_variable_declaration
    # e.g., boolean isValid = validate();
    if parent.type == "variable_declarator":
        for child in parent.children:
            if child.type == "identifier":
                return _text(child, source)

    return None


def _text(node, source: bytes) -> str:
    return source[node.start_byte : node.end_byte].decode("utf-8")
