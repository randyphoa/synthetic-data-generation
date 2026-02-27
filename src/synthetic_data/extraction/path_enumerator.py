"""Phase 2a: Enumerate all entry-to-leaf paths through the CFG."""

from __future__ import annotations

from synthetic_data.extraction.java_conditions import extract_conditions
from synthetic_data.models.cfg_node import (
    CFG,
    CFGNode,
    AssignmentNode,
    DecisionNode,
    EntryNode,
    LeafNode,
    Parameter,
    StatementNode,
)
from synthetic_data.models.condition import (
    AndExpr,
    AtomicExpr,
    Condition,
    ConditionExpr,
    Constraint,
    NotExpr,
    OrExpr,
    Path,
)


def enumerate_paths(
    cfg: CFG,
    parameters: list[Parameter] | None = None,
) -> list[Path]:
    """Enumerate all entry-to-leaf paths through the CFG.

    Returns a list of Paths, each with a conjunctive constraint set.
    Compound conditions (&&, ||) are expanded so each path has a flat
    list of atomic constraints.
    """
    if parameters is None:
        parameters = cfg.method_info.parameters if cfg.method_info else []

    # Extract condition expressions for each decision node
    cond_exprs: dict[int, ConditionExpr] = {}
    for node in cfg.nodes:
        if isinstance(node, DecisionNode):
            cond_exprs[node.id] = extract_conditions(node, parameters)

    # DFS from entry, collecting constraint sets
    raw_paths: list[tuple[list[Constraint], LeafNode]] = []
    _dfs(cfg.entry, [], cond_exprs, raw_paths)

    # Build Path objects
    paths: list[Path] = []
    for i, (constraints, leaf) in enumerate(raw_paths):
        paths.append(
            Path(
                id=i + 1,
                constraints=constraints,
                leaf_type=leaf.leaf_type,
                leaf_value=leaf.value_expr,
            )
        )

    return paths


def _dfs(
    node: CFGNode,
    current_constraints: list[Constraint],
    cond_exprs: dict[int, ConditionExpr],
    results: list[tuple[list[Constraint], LeafNode]],
):
    """DFS traversal of the CFG, collecting constraints along each path."""
    if isinstance(node, LeafNode):
        results.append((list(current_constraints), node))
        return

    if isinstance(node, EntryNode):
        for succ in node.successors:
            _dfs(succ, current_constraints, cond_exprs, results)
        return

    if isinstance(node, StatementNode):
        for succ in node.successors:
            _dfs(succ, current_constraints, cond_exprs, results)
        return

    if isinstance(node, AssignmentNode):
        # Synthetic node from callee inlining — add a constraint binding
        # the target variable to the callee's return value / field assignment
        new_constraints = list(current_constraints)
        if node.target and node.value_expr is not None:
            synthetic = Constraint(
                condition=Condition(
                    variable=node.target,
                    operator="==",
                    value=_parse_assignment_value(node.value_expr, node.java_type),
                    java_type=node.java_type or _guess_assignment_type(node.value_expr),
                    source_expr=f"{node.target} == {node.value_expr}",
                    solver="z3",
                ),
                negated=False,
            )
            new_constraints.append(synthetic)
        for succ in node.successors:
            _dfs(succ, new_constraints, cond_exprs, results)
        return

    if isinstance(node, DecisionNode):
        expr = cond_exprs.get(node.id)

        # True branch: expand condition to DNF (conjunctive constraint sets)
        if node.true_branch is not None:
            if expr is not None:
                true_options = _expand_to_dnf(expr, negated=False)
            else:
                true_options = [[]]
            for option in true_options:
                _dfs(
                    node.true_branch,
                    current_constraints + option,
                    cond_exprs,
                    results,
                )

        # False branch: expand NOT(condition) to DNF
        if node.false_branch is not None:
            if expr is not None:
                false_options = _expand_to_dnf(expr, negated=True)
            else:
                false_options = [[]]
            for option in false_options:
                _dfs(
                    node.false_branch,
                    current_constraints + option,
                    cond_exprs,
                    results,
                )


def _expand_to_dnf(
    expr: ConditionExpr, negated: bool = False
) -> list[list[Constraint]]:
    """Expand a condition expression into disjunctive normal form.

    Returns a list of conjunctions (list of constraints), where the
    overall expression is the OR of these conjunctions.

    Handles short-circuit semantics:
    - true branch of (a || b): sub-path where a is true, OR sub-path
      where a is false but b is true
    - false branch of (a && b): sub-path where a is false, OR sub-path
      where a is true but b is false
    """
    if isinstance(expr, AtomicExpr):
        return [[Constraint(condition=expr.condition, negated=negated)]]

    if isinstance(expr, NotExpr):
        return _expand_to_dnf(expr.operand, not negated)

    if isinstance(expr, AndExpr):
        if not negated:
            # a AND b: cross-product of DNF expansions
            left_dnf = _expand_to_dnf(expr.left, False)
            right_dnf = _expand_to_dnf(expr.right, False)
            return [l + r for l in left_dnf for r in right_dnf]
        else:
            # NOT(a AND b) = !a OR (a AND !b)  [short-circuit]
            left_false = _expand_to_dnf(expr.left, True)
            left_true = _expand_to_dnf(expr.left, False)
            right_false = _expand_to_dnf(expr.right, True)
            result = list(left_false)
            for lt in left_true:
                for rf in right_false:
                    result.append(lt + rf)
            return result

    if isinstance(expr, OrExpr):
        if not negated:
            # a OR b = a, OR (!a AND b)  [short-circuit]
            left_true = _expand_to_dnf(expr.left, False)
            left_false = _expand_to_dnf(expr.left, True)
            right_true = _expand_to_dnf(expr.right, False)
            result = list(left_true)
            for lf in left_false:
                for rt in right_true:
                    result.append(lf + rt)
            return result
        else:
            # NOT(a OR b) = !a AND !b
            left_dnf = _expand_to_dnf(expr.left, True)
            right_dnf = _expand_to_dnf(expr.right, True)
            return [l + r for l in left_dnf for r in right_dnf]

    # Fallback
    return [[]]


def _parse_assignment_value(value_expr: str, java_type: str):
    """Parse a value expression from an AssignmentNode into a Python value."""
    text = value_expr.strip()

    # Boolean literals
    if text == "true":
        return True
    if text == "false":
        return False

    # Null
    if text == "null":
        return None

    # String literals
    if text.startswith('"') and text.endswith('"'):
        return text[1:-1]

    # Numeric literals
    cleaned = text.rstrip("lLfFdD")
    try:
        return int(cleaned)
    except ValueError:
        pass
    try:
        return float(cleaned)
    except ValueError:
        pass

    # Fallback — return as string (will be handled by LLM solver)
    return text


def _guess_assignment_type(value_expr: str) -> str:
    """Guess the Java type from a value expression string."""
    text = value_expr.strip()
    if text in ("true", "false"):
        return "boolean"
    if text.startswith('"'):
        return "String"
    if text == "null":
        return ""
    if "." in text:
        try:
            float(text.rstrip("fFdD"))
            return "double"
        except ValueError:
            pass
    try:
        int(text.rstrip("lL"))
        return "int"
    except ValueError:
        pass
    return ""
