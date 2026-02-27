from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import extract_methods, parse_file


def test_enumerate_paths_count(customer_classifier_path):
    """CustomerClassifier should produce 8 raw paths (6 reachable + 2 dead)."""
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    paths = enumerate_paths(cfg)

    # Due to DNF expansion of `income > 50000 && isMember` false branch,
    # we get 8 total paths. 6 are meaningful, 2 have contradictory constraints.
    assert len(paths) == 8


def test_all_leaf_values_present(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    paths = enumerate_paths(cfg)

    leaf_values = {p.leaf_value for p in paths}
    expected = {
        '"junior"',
        '"senior_member"',
        '"senior"',
        '"premium"',
        '"standard_plus"',
        '"standard"',
    }
    assert leaf_values == expected


def test_path_constraints_junior(customer_classifier_path):
    """Path to 'junior' should have single constraint: age < 18."""
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    paths = enumerate_paths(cfg)

    junior_paths = [p for p in paths if p.leaf_value == '"junior"']
    assert len(junior_paths) == 1
    p = junior_paths[0]

    assert len(p.constraints) == 1
    c = p.constraints[0]
    assert c.condition.variable == "age"
    assert c.condition.operator == "<"
    assert c.condition.value == 18
    assert c.negated is False


def test_path_constraints_premium(customer_classifier_path):
    """Path to 'premium' should require: NOT(age<18), NOT(age>=65),
    income>50000, isMember==true."""
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    paths = enumerate_paths(cfg)

    premium_paths = [p for p in paths if p.leaf_value == '"premium"']
    assert len(premium_paths) == 1
    p = premium_paths[0]

    assert len(p.constraints) == 4

    # Collect constraint info
    constraint_info = [
        (c.condition.variable, c.condition.operator, c.negated) for c in p.constraints
    ]

    # NOT(age < 18)
    assert ("age", "<", True) in constraint_info
    # NOT(age >= 65)
    assert ("age", ">=", True) in constraint_info
    # income > 50000 (not negated)
    assert ("income", ">", False) in constraint_info
    # isMember == True (not negated)
    assert ("isMember", "==", False) in constraint_info


def test_all_paths_are_return_type(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    paths = enumerate_paths(cfg)

    for p in paths:
        assert p.leaf_type == "return"


def test_path_ids_are_sequential(customer_classifier_path):
    tree, source = parse_file(str(customer_classifier_path))
    methods = extract_methods(tree, source)
    cfg = build_cfg(methods[0])

    paths = enumerate_paths(cfg)

    ids = [p.id for p in paths]
    assert ids == list(range(1, len(paths) + 1))
