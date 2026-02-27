from synthetic_data.models.cfg_node import DecisionNode, EntryNode, LeafNode
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import extract_methods, parse_file


def test_build_cfg_structure(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    assert isinstance(cfg.entry, EntryNode)
    assert len(cfg.entry.successors) == 1

    # First decision: age < 18
    d1 = cfg.entry.successors[0]
    assert isinstance(d1, DecisionNode)
    assert d1.condition_expr == "age < 18"


def test_cfg_has_correct_decisions(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    decisions = [n for n in cfg.nodes if isinstance(n, DecisionNode)]
    leaves = [n for n in cfg.nodes if isinstance(n, LeafNode)]

    # 5 decision nodes: age<18, age>=65, isMember, income>50000&&isMember, income>50000
    assert len(decisions) == 5
    # 6 leaf nodes (returns)
    assert len(leaves) == 6


def test_cfg_leaf_values(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    leaves = [n for n in cfg.nodes if isinstance(n, LeafNode)]
    values = sorted([l.value_expr for l in leaves])
    expected = sorted(
        [
            '"junior"',
            '"senior_member"',
            '"senior"',
            '"premium"',
            '"standard_plus"',
            '"standard"',
        ]
    )
    assert values == expected


def test_cfg_decision_chain(customer_classifier_path):
    """Verify the decision chain: age<18 -> age>=65 -> isMember (true branch)."""
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    d1 = cfg.entry.successors[0]
    assert isinstance(d1, DecisionNode)
    assert d1.condition_expr == "age < 18"

    # True branch: return "junior"
    assert isinstance(d1.true_branch, LeafNode)
    assert d1.true_branch.value_expr == '"junior"'

    # False branch: age >= 65
    d2 = d1.false_branch
    assert isinstance(d2, DecisionNode)
    assert d2.condition_expr == "age >= 65"

    # d2 true -> isMember check
    d3 = d2.true_branch
    assert isinstance(d3, DecisionNode)
    assert d3.condition_expr == "isMember"
