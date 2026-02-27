"""Tests for same-class call graph detection."""

from pathlib import Path

from synthetic_data.parsing.call_graph_builder import build_call_graph
from synthetic_data.parsing.java_parser import (
    extract_class_name,
    extract_fields,
    extract_methods,
    parse_file,
    parse_source,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures"


class TestExtractClassName:
    def test_extracts_class_name(self):
        tree, source = parse_source(
            "public class MyService { void foo() {} }"
        )
        assert extract_class_name(tree, source) == "MyService"

    def test_returns_none_for_no_class(self):
        tree, source = parse_source("interface Foo {}")
        assert extract_class_name(tree, source) is None


class TestExtractFields:
    def test_extracts_instance_fields(self):
        tree, source = parse_source("""
        public class Svc {
            private boolean isValid;
            private int count;
            private static String NAME = "test";
            void foo() {}
        }
        """)
        fields = extract_fields(tree, source)
        names = {f.name for f in fields}
        assert "isValid" in names
        assert "count" in names
        # Static field should be excluded
        assert "NAME" not in names

    def test_field_types(self):
        tree, source = parse_source("""
        public class Svc {
            private boolean isValid;
            private int count;
        }
        """)
        fields = extract_fields(tree, source)
        field_map = {f.name: f.java_type for f in fields}
        assert field_map["isValid"] == "boolean"
        assert field_map["count"] == "int"


class TestBuildCallGraph:
    def test_service_with_call_chain(self):
        path = FIXTURES_DIR / "ServiceWithCallChain.java"
        tree, source = parse_file(str(path))
        methods = extract_methods(tree, source)
        class_name = extract_class_name(tree, source)
        cg = build_call_graph(methods, source, class_name)

        assert cg.class_name == "ServiceWithCallChain"
        assert set(cg.methods) == {"executeService", "validateInput", "checkApproval"}

        # executeService calls validateInput and checkApproval
        exec_callees = {cs.callee_method for cs in cg.callees_of("executeService")}
        assert "validateInput" in exec_callees
        assert "checkApproval" in exec_callees

        # validateInput and checkApproval have no same-class calls
        assert len(cg.callees_of("validateInput")) == 0
        assert len(cg.callees_of("checkApproval")) == 0

    def test_result_variable_detection(self):
        tree, source = parse_source("""
        public class Svc {
            public void entry() {
                boolean result = compute();
            }
            private boolean compute() { return true; }
        }
        """)
        methods = extract_methods(tree, source)
        cg = build_call_graph(methods, source, "Svc")
        sites = cg.callees_of("entry")
        assert len(sites) == 1
        assert sites[0].result_variable == "result"

    def test_no_receiver_call(self):
        """Calls without a receiver (implicit this) should be detected."""
        tree, source = parse_source("""
        public class Svc {
            public void entry() { helper(); }
            private void helper() {}
        }
        """)
        methods = extract_methods(tree, source)
        cg = build_call_graph(methods, source, "Svc")
        assert len(cg.callees_of("entry")) == 1
        assert cg.callees_of("entry")[0].callee_method == "helper"

    def test_this_receiver_call(self):
        """Calls with explicit this. receiver should be detected."""
        tree, source = parse_source("""
        public class Svc {
            public void entry() { this.helper(); }
            private void helper() {}
        }
        """)
        methods = extract_methods(tree, source)
        cg = build_call_graph(methods, source, "Svc")
        assert len(cg.callees_of("entry")) == 1

    def test_external_call_ignored(self):
        """Calls on other objects should not be in the call graph."""
        tree, source = parse_source("""
        public class Svc {
            public void entry() { other.helper(); }
            private void helper() {}
        }
        """)
        methods = extract_methods(tree, source)
        cg = build_call_graph(methods, source, "Svc")
        assert len(cg.callees_of("entry")) == 0

    def test_topological_order(self):
        path = FIXTURES_DIR / "ServiceWithCallChain.java"
        tree, source = parse_file(str(path))
        methods = extract_methods(tree, source)
        cg = build_call_graph(methods, source, "ServiceWithCallChain")
        order = cg.topological_order()

        # Leaf methods should come before their callers
        vi_idx = order.index("validateInput")
        ca_idx = order.index("checkApproval")
        es_idx = order.index("executeService")
        assert vi_idx < es_idx
        assert ca_idx < es_idx
