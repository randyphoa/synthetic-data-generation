"""Tests for object getter flattening (Enhancement 3)."""

from synthetic_data.extraction.java_conditions import extract_conditions
from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.models.cfg_node import DecisionNode, Parameter
from synthetic_data.models.condition import AtomicExpr
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import extract_methods, parse_source
from synthetic_data.pipeline import _collect_synthetic_params
from synthetic_data.solving.z3_solver import solve_paths

JAVA_GETTER_COMPARISON = """\
public class PolicyCheck {
    public String check(PolicyObj inspol, int mslImplDte) {
        if (inspol.getComdteC() >= mslImplDte) {
            return "valid";
        }
        return "expired";
    }
}
"""


def test_getter_flattening_in_comparison():
    """inspol.getComdteC() >= mslImplDte should flatten to inspol__comdteC >= mslImplDte."""
    tree, source = parse_source(JAVA_GETTER_COMPARISON)
    methods = extract_methods(tree, source)
    m = methods[0]

    cfg = build_cfg(m)
    d1 = cfg.entry.successors[0]
    assert isinstance(d1, DecisionNode)

    expr = extract_conditions(d1, m.parameters)
    assert isinstance(expr, AtomicExpr)
    cond = expr.condition
    assert cond.solver == "z3"
    assert cond.operator == ">="
    # The getter should be flattened
    assert cond.variable == "inspol__comdteC"
    assert cond.value == "mslImplDte"


def test_getter_flattening_end_to_end():
    """Full pipeline: getter flattening should produce solvable paths."""
    tree, source = parse_source(JAVA_GETTER_COMPARISON)
    methods = extract_methods(tree, source)
    m = methods[0]

    cfg = build_cfg(m)
    params = list(m.parameters)
    paths = enumerate_paths(cfg, params)
    assert len(paths) >= 2

    # Collect synthetic params (inspol__comdteC should be discovered)
    synthetic = _collect_synthetic_params(paths, params)
    synthetic_names = {p.name for p in synthetic}
    assert "inspol__comdteC" in synthetic_names

    all_params = params + synthetic
    results = solve_paths(paths, all_params)
    sat_results = [r for r in results if r.satisfiable and r.values]
    assert len(sat_results) >= 2

    # Both inspol__comdteC and mslImplDte should have concrete values
    for r in sat_results:
        assert "inspol__comdteC" in r.values
        assert "mslImplDte" in r.values


JAVA_GETTER_WITH_UTILITY = """\
public class MixedCheck {
    public String check(PolicyObj inspol, int mslImplDte) {
        if (MSHUtil.isGreaterThanOrEqualsInt(inspol.getComdteC(), mslImplDte)) {
            return "valid";
        }
        return "expired";
    }
}
"""


def test_getter_with_utility_method():
    """Getter inside utility method call should be flattened correctly."""
    tree, source = parse_source(JAVA_GETTER_WITH_UTILITY)
    methods = extract_methods(tree, source)
    m = methods[0]

    cfg = build_cfg(m)
    d1 = cfg.entry.successors[0]
    assert isinstance(d1, DecisionNode)

    expr = extract_conditions(d1, m.parameters)
    assert isinstance(expr, AtomicExpr)
    cond = expr.condition
    assert cond.solver == "z3"
    assert cond.operator == ">="
    assert cond.variable == "inspol__comdteC"
    assert cond.value == "mslImplDte"


JAVA_UTILITY_SIMPLE = """\
public class SimpleUtil {
    public String check(int a, int b) {
        if (MSHUtil.isEqualsInt(a, b)) {
            return "equal";
        }
        return "not_equal";
    }
}
"""


def test_utility_method_two_params():
    """MSHUtil.isEqualsInt(a, b) should resolve to a == b with solver=z3."""
    tree, source = parse_source(JAVA_UTILITY_SIMPLE)
    methods = extract_methods(tree, source)
    m = methods[0]

    cfg = build_cfg(m)
    d1 = cfg.entry.successors[0]
    assert isinstance(d1, DecisionNode)

    expr = extract_conditions(d1, m.parameters)
    assert isinstance(expr, AtomicExpr)
    cond = expr.condition
    assert cond.solver == "z3"
    assert cond.operator == "=="
    assert cond.variable == "a"
    assert cond.value == "b"


JAVA_UTILITY_FLIPPED = """\
public class FlippedUtil {
    public String check(int param) {
        if (MSHUtil.isGreaterThanInt(100, param)) {
            return "big";
        }
        return "small";
    }
}
"""


def test_utility_method_flipped_args():
    """When param is second arg, operator should be flipped."""
    tree, source = parse_source(JAVA_UTILITY_FLIPPED)
    methods = extract_methods(tree, source)
    m = methods[0]

    cfg = build_cfg(m)
    d1 = cfg.entry.successors[0]
    assert isinstance(d1, DecisionNode)

    expr = extract_conditions(d1, m.parameters)
    assert isinstance(expr, AtomicExpr)
    cond = expr.condition
    assert cond.solver == "z3"
    # isGreaterThanInt(100, param) means 100 > param, so param < 100
    assert cond.variable == "param"
    assert cond.operator == "<"
    assert cond.value == 100


JAVA_ONE_ARG_UTILITY = """\
public class NullCheck {
    public String check(String name) {
        if (ObjectUtils.isEmpty(name)) {
            return "empty";
        }
        return "present";
    }
}
"""


def test_one_arg_utility_method():
    """ObjectUtils.isEmpty(name) should resolve to name == null."""
    tree, source = parse_source(JAVA_ONE_ARG_UTILITY)
    methods = extract_methods(tree, source)
    m = methods[0]

    cfg = build_cfg(m)
    d1 = cfg.entry.successors[0]
    assert isinstance(d1, DecisionNode)

    expr = extract_conditions(d1, m.parameters)
    assert isinstance(expr, AtomicExpr)
    cond = expr.condition
    assert cond.solver == "z3"
    assert cond.variable == "name"
    assert cond.operator == "=="
    assert cond.value is None  # null check
