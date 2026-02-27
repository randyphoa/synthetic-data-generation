"""Tests for Phase 4: Dataset assembly."""

import csv
import json
import tempfile
from pathlib import Path as FilePath

import pytest

from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.generation.dataset import (
    _deduplicate,
    _to_csv,
    _to_json,
    assemble,
    build_path_map,
)
from synthetic_data.models.cfg_node import Parameter
from synthetic_data.models.condition import Condition, Constraint, Path
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.java_parser import extract_methods, parse_file
from synthetic_data.solving.boundary import (
    DataRow,
    generate_boundary_rows,
    generate_edge_case_rows,
)
from synthetic_data.solving.z3_solver import solve_paths


def _make_condition(variable, operator, value, java_type="int"):
    return Condition(
        variable=variable,
        operator=operator,
        value=value,
        java_type=java_type,
        source_expr=f"{variable} {operator} {value}",
        solver="z3",
    )


def _make_path(path_id, constraints, leaf_value="result"):
    return Path(
        id=path_id,
        constraints=constraints,
        leaf_type="return",
        leaf_value=leaf_value,
    )


def _make_row(values, path_id, row_type="path"):
    return DataRow(
        values=values,
        path_id=path_id,
        row_type=row_type,
        source=f"test {row_type}",
    )


# --- Deduplication ---


class TestDeduplicate:
    def test_removes_exact_duplicates(self):
        rows = [
            _make_row({"x": 1, "y": 2}, path_id=1),
            _make_row({"x": 1, "y": 2}, path_id=1),
        ]
        result = _deduplicate(rows)
        assert len(result) == 1

    def test_keeps_different_values(self):
        rows = [
            _make_row({"x": 1}, path_id=1),
            _make_row({"x": 2}, path_id=1),
        ]
        result = _deduplicate(rows)
        assert len(result) == 2

    def test_keeps_same_values_different_paths(self):
        rows = [
            _make_row({"x": 1}, path_id=1),
            _make_row({"x": 1}, path_id=2),
        ]
        result = _deduplicate(rows)
        assert len(result) == 2

    def test_empty_input(self):
        assert _deduplicate([]) == []

    def test_preserves_order(self):
        rows = [
            _make_row({"x": 3}, path_id=1),
            _make_row({"x": 1}, path_id=1),
            _make_row({"x": 3}, path_id=1),  # dup
            _make_row({"x": 2}, path_id=1),
        ]
        result = _deduplicate(rows)
        assert [r.values["x"] for r in result] == [3, 1, 2]


# --- Path mapping ---


class TestBuildPathMap:
    def test_maps_values_and_expected_output(self):
        paths = [_make_path(1, [], leaf_value='"junior"')]
        rows = [_make_row({"age": 10}, path_id=1)]

        mapped = build_path_map(rows, paths)

        assert len(mapped) == 1
        assert mapped[0]["age"] == 10
        assert mapped[0]["expected_output"] == '"junior"'
        assert mapped[0]["path_id"] == 1
        assert mapped[0]["row_type"] == "path"

    def test_unknown_path_id_gives_none_output(self):
        paths = [_make_path(1, [], leaf_value='"junior"')]
        rows = [_make_row({"age": 10}, path_id=99)]

        mapped = build_path_map(rows, paths)

        assert mapped[0]["expected_output"] is None

    def test_multiple_rows_multiple_paths(self):
        paths = [
            _make_path(1, [], leaf_value='"junior"'),
            _make_path(2, [], leaf_value='"senior"'),
        ]
        rows = [
            _make_row({"age": 10}, path_id=1),
            _make_row({"age": 70}, path_id=2),
        ]

        mapped = build_path_map(rows, paths)

        assert len(mapped) == 2
        assert mapped[0]["expected_output"] == '"junior"'
        assert mapped[1]["expected_output"] == '"senior"'

    def test_row_type_preserved(self):
        paths = [_make_path(1, [], leaf_value='"result"')]
        rows = [
            _make_row({"x": 1}, path_id=1, row_type="boundary"),
        ]

        mapped = build_path_map(rows, paths)
        assert mapped[0]["row_type"] == "boundary"


# --- CSV output ---


class TestCSVOutput:
    def test_csv_columns(self):
        params = [Parameter("age", "int"), Parameter("income", "double")]
        paths = [_make_path(1, [], leaf_value='"junior"')]
        rows = [_make_row({"age": 10, "income": 30000.0}, path_id=1)]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            _to_csv(rows, params, paths, f.name)
            f.flush()

            with open(f.name) as rf:
                reader = csv.DictReader(rf)
                fieldnames = reader.fieldnames
                data = list(reader)

        assert fieldnames == ["age", "income", "expected_output", "path_id", "row_type"]
        assert len(data) == 1
        assert data[0]["age"] == "10"
        assert data[0]["income"] == "30000.0"
        assert data[0]["expected_output"] == '"junior"'
        assert data[0]["path_id"] == "1"
        assert data[0]["row_type"] == "path"

    def test_csv_multiple_rows(self):
        params = [Parameter("x", "int")]
        paths = [
            _make_path(1, [], leaf_value='"a"'),
            _make_path(2, [], leaf_value='"b"'),
        ]
        rows = [
            _make_row({"x": 1}, path_id=1),
            _make_row({"x": 2}, path_id=2),
            _make_row({"x": 3}, path_id=1, row_type="boundary"),
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            _to_csv(rows, params, paths, f.name)

            with open(f.name) as rf:
                data = list(csv.DictReader(rf))

        assert len(data) == 3


# --- JSON output ---


class TestJSONOutput:
    def test_json_structure(self):
        params = [Parameter("age", "int"), Parameter("income", "double")]
        paths = [_make_path(1, [], leaf_value='"junior"')]
        rows = [_make_row({"age": 10, "income": 30000.0}, path_id=1)]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            _to_json(rows, params, paths, f.name)

            with open(f.name) as rf:
                data = json.load(rf)

        assert len(data) == 1
        entry = data[0]
        assert "parameters" in entry
        assert entry["parameters"]["age"] == 10
        assert entry["parameters"]["income"] == 30000.0
        assert entry["expected_output"] == '"junior"'
        assert entry["path_id"] == 1
        assert entry["row_type"] == "path"

    def test_json_parameter_ordering(self):
        params = [Parameter("b", "int"), Parameter("a", "int")]
        paths = [_make_path(1, [], leaf_value='"r"')]
        rows = [_make_row({"a": 1, "b": 2}, path_id=1)]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            _to_json(rows, params, paths, f.name)

            with open(f.name) as rf:
                data = json.load(rf)

        # Parameters should follow the parameter list order
        keys = list(data[0]["parameters"].keys())
        assert keys == ["b", "a"]


# --- assemble() ---


class TestAssemble:
    def test_assemble_csv(self):
        params = [Parameter("x", "int")]
        paths = [_make_path(1, [], leaf_value='"result"')]
        path_rows = [_make_row({"x": 5}, path_id=1)]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                path_rows, [], [], paths, params,
                format="csv",
                output_path=f"{tmpdir}/out.csv",
            )

            assert FilePath(out).exists()
            with open(out) as f:
                reader = csv.DictReader(f)
                data = list(reader)
            assert len(data) == 1

    def test_assemble_json(self):
        params = [Parameter("x", "int")]
        paths = [_make_path(1, [], leaf_value='"result"')]
        path_rows = [_make_row({"x": 5}, path_id=1)]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                path_rows, [], [], paths, params,
                format="json",
                output_path=f"{tmpdir}/out.json",
            )

            assert FilePath(out).exists()
            with open(out) as f:
                data = json.load(f)
            assert len(data) == 1

    def test_assemble_merges_all_row_types(self):
        params = [Parameter("x", "int")]
        paths = [_make_path(1, [], leaf_value='"r"')]

        path_rows = [_make_row({"x": 1}, path_id=1, row_type="path")]
        boundary_rows = [_make_row({"x": 2}, path_id=1, row_type="boundary")]
        edge_rows = [_make_row({"x": 3}, path_id=1, row_type="edge_case")]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                path_rows, boundary_rows, edge_rows, paths, params,
                format="csv",
                output_path=f"{tmpdir}/out.csv",
            )

            with open(out) as f:
                data = list(csv.DictReader(f))

        assert len(data) == 3
        row_types = {d["row_type"] for d in data}
        assert row_types == {"path", "boundary", "edge_case"}

    def test_assemble_deduplicates(self):
        params = [Parameter("x", "int")]
        paths = [_make_path(1, [], leaf_value='"r"')]

        dup_rows = [
            _make_row({"x": 1}, path_id=1, row_type="path"),
            _make_row({"x": 1}, path_id=1, row_type="boundary"),  # same values+path
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                dup_rows, [], [], paths, params,
                format="csv",
                output_path=f"{tmpdir}/out.csv",
            )

            with open(out) as f:
                data = list(csv.DictReader(f))

        assert len(data) == 1

    def test_assemble_default_path(self):
        params = [Parameter("x", "int")]
        paths = [_make_path(1, [], leaf_value='"r"')]
        rows = [_make_row({"x": 1}, path_id=1)]

        with tempfile.TemporaryDirectory() as tmpdir:
            import os
            old_cwd = os.getcwd()
            os.chdir(tmpdir)
            try:
                out = assemble(rows, [], [], paths, params, format="csv")
                assert FilePath(out).exists()
                assert out == "dataset.csv"
            finally:
                os.chdir(old_cwd)


# --- End-to-end with CustomerClassifier ---


class TestCustomerClassifierDataset:
    def test_end_to_end_csv(self, customer_classifier_path):
        """Full pipeline: parse → paths → solve → boundary → assemble CSV."""
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        # Solve paths
        results = solve_paths(paths, params)
        path_rows = [
            DataRow(
                values=r.values,
                path_id=r.path_id,
                row_type="path",
                source="z3 solver",
            )
            for r in results
            if r.satisfiable and r.values
        ]

        # Generate boundary and edge case rows
        boundary_rows = generate_boundary_rows(paths, params)
        edge_rows = generate_edge_case_rows(paths, params)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                path_rows, boundary_rows, edge_rows, paths, params,
                format="csv",
                output_path=f"{tmpdir}/classifier.csv",
            )

            with open(out) as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames
                data = list(reader)

        # Check columns
        assert "age" in fieldnames
        assert "income" in fieldnames
        assert "isMember" in fieldnames
        assert "expected_output" in fieldnames
        assert "path_id" in fieldnames
        assert "row_type" in fieldnames

        # Should have a reasonable number of rows
        assert len(data) > 0

        # All row types should be present
        row_types = {d["row_type"] for d in data}
        assert "path" in row_types
        assert "boundary" in row_types
        assert "edge_case" in row_types

    def test_end_to_end_json(self, customer_classifier_path):
        """Full pipeline outputting JSON."""
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        results = solve_paths(paths, params)
        path_rows = [
            DataRow(
                values=r.values,
                path_id=r.path_id,
                row_type="path",
                source="z3 solver",
            )
            for r in results
            if r.satisfiable and r.values
        ]

        boundary_rows = generate_boundary_rows(paths, params)
        edge_rows = generate_edge_case_rows(paths, params)

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                path_rows, boundary_rows, edge_rows, paths, params,
                format="json",
                output_path=f"{tmpdir}/classifier.json",
            )

            with open(out) as f:
                data = json.load(f)

        assert len(data) > 0
        for entry in data:
            assert "parameters" in entry
            assert "expected_output" in entry
            assert "path_id" in entry
            assert "row_type" in entry

    def test_path_coverage(self, customer_classifier_path):
        """Every reachable path should have at least one row."""
        tree, source = parse_file(str(customer_classifier_path))
        methods = extract_methods(tree, source)
        cfg = build_cfg(methods[0])
        paths = enumerate_paths(cfg)
        params = methods[0].parameters

        results = solve_paths(paths, params)
        path_rows = [
            DataRow(
                values=r.values,
                path_id=r.path_id,
                row_type="path",
                source="z3 solver",
            )
            for r in results
            if r.satisfiable and r.values
        ]

        boundary_rows = generate_boundary_rows(paths, params)
        edge_rows = generate_edge_case_rows(paths, params)

        all_rows = path_rows + boundary_rows + edge_rows
        covered_path_ids = {r.path_id for r in all_rows}
        reachable_path_ids = {p.id for p in paths if p.is_reachable}

        assert reachable_path_ids.issubset(covered_path_ids)
