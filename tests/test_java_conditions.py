from synthetic_data.extraction.java_conditions import extract_conditions
from synthetic_data.models.cfg_node import DecisionNode
from synthetic_data.models.condition import AndExpr, AtomicExpr
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import extract_methods, parse_file


def test_simple_condition(customer_classifier_path):
    """age < 18 should produce a single AtomicExpr."""
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    d1 = cfg.entry.successors[0]
    expr = extract_conditions(d1, methods[0].parameters)

    assert isinstance(expr, AtomicExpr)
    assert expr.condition.variable == "age"
    assert expr.condition.operator == "<"
    assert expr.condition.value == 18
    assert expr.condition.java_type == "int"
    assert expr.condition.solver == "z3"


def test_boolean_condition(customer_classifier_path):
    """isMember (bare boolean) should produce AtomicExpr with == True."""
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    # Navigate to isMember decision: entry -> d1(false) -> d2(true) -> d3
    d1 = cfg.entry.successors[0]
    d2 = d1.false_branch  # age >= 65
    d3 = d2.true_branch  # isMember

    expr = extract_conditions(d3, methods[0].parameters)
    assert isinstance(expr, AtomicExpr)
    assert expr.condition.variable == "isMember"
    assert expr.condition.operator == "=="
    assert expr.condition.value is True
    assert expr.condition.solver == "z3"


def test_compound_and_condition(customer_classifier_path):
    """income > 50000 && isMember should produce AndExpr."""
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    # Navigate: entry -> d1(false) -> d2(false) -> d4
    d1 = cfg.entry.successors[0]
    d2 = d1.false_branch
    d4 = d2.false_branch  # income > 50000 && isMember

    expr = extract_conditions(d4, methods[0].parameters)
    assert isinstance(expr, AndExpr)

    # Left: income > 50000
    assert isinstance(expr.left, AtomicExpr)
    assert expr.left.condition.variable == "income"
    assert expr.left.condition.operator == ">"
    assert expr.left.condition.value == 50000.0
    assert expr.left.condition.java_type == "double"

    # Right: isMember
    assert isinstance(expr.right, AtomicExpr)
    assert expr.right.condition.variable == "isMember"
    assert expr.right.condition.operator == "=="
    assert expr.right.condition.value is True
