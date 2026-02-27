"""Tests for constructor-to-field linking (Enhancement 2)."""

from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.models.cfg_node import Parameter
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import (
    extract_constructor_field_map,
    extract_constructors,
    extract_methods,
    parse_source,
)
from synthetic_data.solving.z3_solver import solve_paths

JAVA_CLASS_WITH_CONSTRUCTOR = """\
public class PremiumPayer {
    private int inProcMode;
    private String inInsuredCode;

    public PremiumPayer(int procMode, String insuredCode) {
        this.inProcMode = procMode;
        this.inInsuredCode = insuredCode;
    }

    public String executeService() {
        if (inProcMode < 10) {
            return "low";
        } else if (inProcMode >= 100) {
            return "high";
        }
        return "medium";
    }
}
"""


def test_extract_constructors():
    """Should find the constructor and its parameters."""
    tree, source = parse_source(JAVA_CLASS_WITH_CONSTRUCTOR)
    constructors = extract_constructors(tree, source)

    assert len(constructors) == 1
    ctor = constructors[0]
    assert ctor.name == "PremiumPayer"
    assert len(ctor.parameters) == 2
    assert ctor.parameters[0].name == "procMode"
    assert ctor.parameters[0].java_type == "int"
    assert ctor.parameters[1].name == "insuredCode"
    assert ctor.parameters[1].java_type == "String"


def test_extract_constructor_field_map():
    """Should map this.field = param assignments."""
    tree, source = parse_source(JAVA_CLASS_WITH_CONSTRUCTOR)
    field_map = extract_constructor_field_map(tree, source)

    assert field_map == {
        "inProcMode": "procMode",
        "inInsuredCode": "insuredCode",
    }


def test_constructor_virtual_params_end_to_end():
    """Parameterless method should produce paths using constructor field params."""
    from synthetic_data.pipeline import _build_constructor_virtual_params, _find_used_virtual_params

    tree, source = parse_source(JAVA_CLASS_WITH_CONSTRUCTOR)
    constructors = extract_constructors(tree, source)
    field_map = extract_constructor_field_map(tree, source)
    virtual_params = _build_constructor_virtual_params(constructors, field_map)

    assert "inProcMode" in virtual_params
    assert virtual_params["inProcMode"].java_type == "int"
    assert "inInsuredCode" in virtual_params
    assert virtual_params["inInsuredCode"].java_type == "String"

    # Get the executeService method
    methods = extract_methods(tree, source)
    exec_method = [m for m in methods if m.name == "executeService"][0]
    assert len(exec_method.parameters) == 0  # No explicit params

    # Find used virtual params
    used = _find_used_virtual_params(exec_method, virtual_params, source)
    used_names = {p.name for p in used}
    assert "inProcMode" in used_names
    # inInsuredCode is not used in executeService, so it should not be included
    assert "inInsuredCode" not in used_names

    # Build CFG and enumerate paths using virtual params
    cfg = build_cfg(exec_method)
    paths = enumerate_paths(cfg, used)
    assert len(paths) >= 2  # At least low and high paths

    # Solve paths
    results = solve_paths(paths, used)
    sat_results = [r for r in results if r.satisfiable and r.values]
    assert len(sat_results) >= 2

    # Check that inProcMode has concrete values
    for r in sat_results:
        assert "inProcMode" in r.values


JAVA_NO_CONSTRUCTOR = """\
public class Simple {
    public String doWork(int x) {
        if (x > 0) { return "pos"; }
        return "neg";
    }
}
"""


def test_no_constructor_no_change():
    """Classes without constructors should produce empty field map."""
    tree, source = parse_source(JAVA_NO_CONSTRUCTOR)
    constructors = extract_constructors(tree, source)
    assert len(constructors) == 0

    field_map = extract_constructor_field_map(tree, source)
    assert field_map == {}
