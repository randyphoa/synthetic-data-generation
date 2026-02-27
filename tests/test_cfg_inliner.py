"""Tests for CFG inlining and end-to-end path enumeration with call chains."""

from pathlib import Path

from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.models.cfg_node import AssignmentNode, DecisionNode, LeafNode
from synthetic_data.parsing.call_graph_builder import build_call_graph
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.cfg_inliner import inline_calls
from synthetic_data.parsing.java_parser import (
    extract_class_name,
    extract_fields,
    extract_methods,
    parse_file,
    parse_source,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _build_everything(source_text):
    """Helper: parse, build CFGs, build call graph, return all pieces."""
    tree, source = parse_source(source_text)
    methods = extract_methods(tree, source)
    class_name = extract_class_name(tree, source)
    fields = extract_fields(tree, source)
    call_graph = build_call_graph(methods, source, class_name)

    cfg_registry = {}
    for m in methods:
        cfg_registry[m.name] = build_cfg(m)

    return tree, source, methods, fields, call_graph, cfg_registry


class TestReturnValueInlining:
    """Test inlining of callees that return values used in caller branches."""

    def test_return_value_creates_assignment_nodes(self):
        source_text = """
        public class Svc {
            public String entry(int x) {
                boolean ok = check(x);
                if (ok) {
                    return "yes";
                } else {
                    return "no";
                }
            }
            private boolean check(int x) {
                if (x > 10) {
                    return true;
                } else {
                    return false;
                }
            }
        }
        """
        _, source, methods, fields, cg, registry = _build_everything(source_text)
        entry_method = [m for m in methods if m.name == "entry"][0]
        entry_cfg = registry["entry"]

        inlined = inline_calls(entry_cfg, cg, registry, source, fields)

        # The inlined CFG should contain AssignmentNode instances
        assignment_nodes = [n for n in inlined.nodes if isinstance(n, AssignmentNode)]
        assert len(assignment_nodes) > 0

        # At least one should assign to "ok"
        ok_assigns = [a for a in assignment_nodes if a.target == "ok"]
        assert len(ok_assigns) >= 1

    def test_return_value_paths(self):
        source_text = """
        public class Svc {
            public String entry(int x) {
                boolean ok = check(x);
                if (ok) {
                    return "yes";
                } else {
                    return "no";
                }
            }
            private boolean check(int x) {
                if (x > 10) {
                    return true;
                } else {
                    return false;
                }
            }
        }
        """
        _, source, methods, fields, cg, registry = _build_everything(source_text)
        entry_method = [m for m in methods if m.name == "entry"][0]
        entry_cfg = registry["entry"]

        inlined = inline_calls(entry_cfg, cg, registry, source, fields)
        paths = enumerate_paths(inlined, entry_method.parameters)

        # Should have paths that include constraints from the callee
        assert len(paths) >= 2

        # Check that some paths carry constraints with "ok" variable
        ok_constraints = []
        for p in paths:
            for c in p.constraints:
                if c.condition.variable == "ok":
                    ok_constraints.append(c)
        assert len(ok_constraints) > 0


class TestFieldSideEffectInlining:
    """Test inlining of callees that set instance fields."""

    def test_field_assignment_detected(self):
        source_text = """
        public class Svc {
            private boolean isValid;

            public String entry(int x) {
                validate(x);
                if (isValid) {
                    return "ok";
                } else {
                    return "fail";
                }
            }
            private void validate(int x) {
                if (x > 0) {
                    this.isValid = true;
                } else {
                    this.isValid = false;
                }
            }
        }
        """
        _, source, methods, fields, cg, registry = _build_everything(source_text)
        entry_method = [m for m in methods if m.name == "entry"][0]
        entry_cfg = registry["entry"]

        inlined = inline_calls(entry_cfg, cg, registry, source, fields)

        # Should have AssignmentNodes for the field
        assignment_nodes = [n for n in inlined.nodes if isinstance(n, AssignmentNode)]
        field_assigns = [a for a in assignment_nodes if a.target == "isValid"]
        assert len(field_assigns) >= 1

    def test_field_side_effect_paths(self):
        source_text = """
        public class Svc {
            private boolean isValid;

            public String entry(int x) {
                validate(x);
                if (isValid) {
                    return "ok";
                } else {
                    return "fail";
                }
            }
            private void validate(int x) {
                if (x > 0) {
                    this.isValid = true;
                } else {
                    this.isValid = false;
                }
            }
        }
        """
        _, source, methods, fields, cg, registry = _build_everything(source_text)
        entry_method = [m for m in methods if m.name == "entry"][0]
        entry_cfg = registry["entry"]

        inlined = inline_calls(entry_cfg, cg, registry, source, fields)
        paths = enumerate_paths(inlined, entry_method.parameters)

        # Should have paths with isValid constraints
        assert len(paths) >= 2
        all_vars = set()
        for p in paths:
            for c in p.constraints:
                all_vars.add(c.condition.variable)
        assert "isValid" in all_vars


class TestServiceWithCallChainFixture:
    """End-to-end test using the ServiceWithCallChain.java fixture."""

    def test_inlined_paths_from_fixture(self):
        path = FIXTURES_DIR / "ServiceWithCallChain.java"
        tree, source = parse_file(str(path))
        methods = extract_methods(tree, source)
        class_name = extract_class_name(tree, source)
        fields = extract_fields(tree, source)
        call_graph = build_call_graph(methods, source, class_name)

        cfg_registry = {}
        for m in methods:
            cfg_registry[m.name] = build_cfg(m)

        # Inline into executeService
        entry_method = [m for m in methods if m.name == "executeService"][0]
        entry_cfg = cfg_registry["executeService"]

        inlined = inline_calls(entry_cfg, call_graph, cfg_registry, source, fields)
        paths = enumerate_paths(inlined, entry_method.parameters)

        # Without inlining, executeService has 3 simple paths
        # With inlining, we should get more paths due to callee branches
        assert len(paths) > 3

        # Check that leaf values include all expected outcomes
        leaf_values = {p.leaf_value for p in paths}
        expected = {'"approved"', '"rejected"', '"invalid"'}
        assert expected.issubset(leaf_values), f"Missing leaves: {expected - leaf_values}"

    def test_without_inlining_fewer_paths(self):
        path = FIXTURES_DIR / "ServiceWithCallChain.java"
        tree, source = parse_file(str(path))
        methods = extract_methods(tree, source)

        entry_method = [m for m in methods if m.name == "executeService"][0]
        cfg = build_cfg(entry_method)

        # Without inlining — only direct paths through executeService
        paths_no_inline = enumerate_paths(cfg, entry_method.parameters)

        # With inlining
        class_name = extract_class_name(tree, source)
        fields = extract_fields(tree, source)
        call_graph = build_call_graph(methods, source, class_name)
        cfg_registry = {m.name: build_cfg(m) for m in methods}
        inlined = inline_calls(
            cfg_registry["executeService"], call_graph, cfg_registry, source, fields
        )
        paths_inlined = enumerate_paths(inlined, entry_method.parameters)

        # Inlined version should have more paths
        assert len(paths_inlined) > len(paths_no_inline)


class TestMaxDepth:
    """Test that max_depth limits inlining."""

    def test_depth_zero_no_inlining(self):
        source_text = """
        public class Svc {
            public String entry(int x) {
                boolean ok = check(x);
                if (ok) { return "yes"; } else { return "no"; }
            }
            private boolean check(int x) {
                if (x > 10) { return true; } else { return false; }
            }
        }
        """
        _, source, methods, fields, cg, registry = _build_everything(source_text)
        entry_cfg = registry["entry"]

        # With max_depth=0, no inlining should occur
        result = inline_calls(entry_cfg, cg, registry, source, fields, max_depth=0)

        # Should be essentially the same as the original
        assignment_nodes = [n for n in result.nodes if isinstance(n, AssignmentNode)]
        assert len(assignment_nodes) == 0


class TestNoCallsUnchanged:
    """Ensure that CFGs without same-class calls are returned unchanged."""

    def test_no_calls(self):
        source_text = """
        public class Svc {
            public String entry(int x) {
                if (x > 10) { return "big"; } else { return "small"; }
            }
        }
        """
        _, source, methods, fields, cg, registry = _build_everything(source_text)
        entry_cfg = registry["entry"]

        result = inline_calls(entry_cfg, cg, registry, source, fields)
        paths = enumerate_paths(result, methods[0].parameters)

        # Should still produce normal paths
        assert len(paths) >= 2
