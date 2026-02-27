"""Tests for column mapping: @Column annotation extraction, name resolution, and flat output."""

from __future__ import annotations

import csv
import json
import tempfile
from pathlib import Path as FilePath

import pytest

from synthetic_data.generation.dataset import _to_csv, _to_json, assemble
from synthetic_data.models.cfg_node import Parameter
from synthetic_data.models.column_mapping import (
    ColumnMapping,
    SchemaInfo,
    build_column_mappings,
    load_schema_from_csv,
)
from synthetic_data.models.condition import Path
from synthetic_data.parsing.java_parser import (
    extract_column_annotations,
    extract_table_name,
    parse_source,
)
from synthetic_data.solving.boundary import DataRow


# --- Fixtures ---

ENTITY_JAVA = """\
package com.example;

import javax.persistence.Column;
import javax.persistence.Entity;
import javax.persistence.Table;

@Entity
@Table(name = "T_INSPOL")
public class INSPOL {

    @Column(name = "INSPOL_STS_TAG")
    private String stsTag;

    @Column(name = "INSPOL_COMDTE_C")
    private Integer comdteC;

    @Column(name = "INSPOL_POL_TP")
    private String polTp;

    // Field without @Column — should be ignored
    private String internalField;
}
"""

ENTITY_NO_TABLE = """\
package com.example;

import javax.persistence.Column;

public class PlainClass {
    @Column(name = "COL_A")
    private String fieldA;
}
"""


def _make_path(path_id, leaf_value="result"):
    return Path(id=path_id, constraints=[], leaf_type="return", leaf_value=leaf_value)


def _make_row(values, path_id, row_type="path"):
    return DataRow(values=values, path_id=path_id, row_type=row_type, source="test")


# --- @Column annotation extraction ---


class TestExtractColumnAnnotations:
    def test_extracts_field_to_column_mapping(self):
        tree, source = parse_source(ENTITY_JAVA)
        mapping = extract_column_annotations(tree, source)

        assert mapping == {
            "stsTag": "INSPOL_STS_TAG",
            "comdteC": "INSPOL_COMDTE_C",
            "polTp": "INSPOL_POL_TP",
        }

    def test_ignores_fields_without_column(self):
        tree, source = parse_source(ENTITY_JAVA)
        mapping = extract_column_annotations(tree, source)

        assert "internalField" not in mapping

    def test_empty_for_no_annotations(self):
        tree, source = parse_source("public class Empty { private int x; }")
        mapping = extract_column_annotations(tree, source)
        assert mapping == {}


class TestExtractTableName:
    def test_extracts_table_name(self):
        tree, source = parse_source(ENTITY_JAVA)
        name = extract_table_name(tree, source)
        assert name == "T_INSPOL"

    def test_none_when_no_table_annotation(self):
        tree, source = parse_source(ENTITY_NO_TABLE)
        name = extract_table_name(tree, source)
        assert name is None

    def test_none_for_plain_class(self):
        tree, source = parse_source("public class Foo { }")
        name = extract_table_name(tree, source)
        assert name is None


# --- ColumnMapping.resolve() ---


class TestColumnMappingResolve:
    def setup_method(self):
        self.mapping = ColumnMapping(
            table_name="T_INSPOL",
            field_to_column={
                "stsTag": "INSPOL_STS_TAG",
                "comdteC": "INSPOL_COMDTE_C",
                "polTp": "INSPOL_POL_TP",
            },
        )

    def test_direct_lookup(self):
        assert self.mapping.resolve("stsTag") == "INSPOL_STS_TAG"
        assert self.mapping.resolve("comdteC") == "INSPOL_COMDTE_C"

    def test_flattened_getter_lookup(self):
        assert self.mapping.resolve("inspol__comdteC") == "INSPOL_COMDTE_C"
        assert self.mapping.resolve("inspol__stsTag") == "INSPOL_STS_TAG"

    def test_unknown_field_returns_none(self):
        assert self.mapping.resolve("unknownField") is None

    def test_unknown_flattened_returns_none(self):
        assert self.mapping.resolve("inspol__unknownField") is None

    def test_dot_getter_lookup(self):
        assert self.mapping.resolve("inspol.getComdteC()") == "INSPOL_COMDTE_C"
        assert self.mapping.resolve("inspol.getStsTag()") == "INSPOL_STS_TAG"

    def test_dot_getter_unknown_returns_none(self):
        assert self.mapping.resolve("inspol.getUnknownField()") is None

    def test_dot_getter_is_prefix(self):
        mapping = ColumnMapping(
            table_name="T_TEST",
            field_to_column={"active": "TEST_ACTIVE"},
        )
        assert mapping.resolve("obj.isActive()") == "TEST_ACTIVE"


# --- Flat JSON output with column mappings ---


class TestFlatJSONOutput:
    def test_flat_json_with_mappings(self):
        params = [Parameter("stsTag", "String"), Parameter("comdteC", "Integer")]
        paths = [_make_path(1, leaf_value='"A"')]
        rows = [_make_row({"stsTag": "E", "comdteC": 20240301}, path_id=1)]

        mappings = [
            ColumnMapping(
                table_name="T_INSPOL",
                field_to_column={
                    "stsTag": "INSPOL_STS_TAG",
                    "comdteC": "INSPOL_COMDTE_C",
                },
            )
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            _to_json(rows, params, paths, f.name, column_mappings=mappings)

            with open(f.name) as rf:
                data = json.load(rf)

        assert len(data) == 1
        entry = data[0]
        # Should be flat (no "parameters" wrapper)
        assert "parameters" not in entry
        assert entry["INSPOL_STS_TAG"] == "E"
        assert entry["INSPOL_COMDTE_C"] == 20240301
        assert entry["expected_output"] == '"A"'
        assert entry["path_id"] == 1

    def test_flattened_getter_names_resolved(self):
        params = [Parameter("inspol__comdteC", "Integer")]
        paths = [_make_path(1)]
        rows = [_make_row({"inspol__comdteC": 20240301}, path_id=1)]

        mappings = [
            ColumnMapping(
                table_name="T_INSPOL",
                field_to_column={"comdteC": "INSPOL_COMDTE_C"},
            )
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            _to_json(rows, params, paths, f.name, column_mappings=mappings)

            with open(f.name) as rf:
                data = json.load(rf)

        assert data[0]["INSPOL_COMDTE_C"] == 20240301

    def test_unmapped_params_excluded(self):
        params = [Parameter("unknownParam", "int")]
        paths = [_make_path(1)]
        rows = [_make_row({"unknownParam": 42}, path_id=1)]

        mappings = [
            ColumnMapping(table_name="T_INSPOL", field_to_column={})
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            _to_json(rows, params, paths, f.name, column_mappings=mappings)

            with open(f.name) as rf:
                data = json.load(rf)

        # Unmapped params should be excluded from flat output
        assert "unknownParam" not in data[0]
        # Metadata fields are still present
        assert "expected_output" in data[0]
        assert "path_id" in data[0]

    def test_mixed_mapped_and_unmapped_params(self):
        params = [
            Parameter("stsTag", "String"),
            Parameter("inProcMode", "String"),
            Parameter("comdteC", "Integer"),
        ]
        paths = [_make_path(1, leaf_value='"A"')]
        rows = [_make_row({"stsTag": "E", "inProcMode": "X", "comdteC": 20240301}, path_id=1)]

        mappings = [
            ColumnMapping(
                table_name="T_INSPOL",
                field_to_column={
                    "stsTag": "INSPOL_STS_TAG",
                    "comdteC": "INSPOL_COMDTE_C",
                },
            )
        ]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            _to_json(rows, params, paths, f.name, column_mappings=mappings)

            with open(f.name) as rf:
                data = json.load(rf)

        entry = data[0]
        # Mapped params appear with SQL column names
        assert entry["INSPOL_STS_TAG"] == "E"
        assert entry["INSPOL_COMDTE_C"] == 20240301
        # Unmapped param is excluded
        assert "inProcMode" not in entry


# --- Flat CSV output with column mappings ---


class TestFlatCSVOutput:
    def test_csv_uses_sql_column_names(self):
        params = [Parameter("stsTag", "String"), Parameter("comdteC", "Integer")]
        paths = [_make_path(1)]
        rows = [_make_row({"stsTag": "E", "comdteC": 20240301}, path_id=1)]

        mappings = [
            ColumnMapping(
                table_name="T_INSPOL",
                field_to_column={
                    "stsTag": "INSPOL_STS_TAG",
                    "comdteC": "INSPOL_COMDTE_C",
                },
            )
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            _to_csv(rows, params, paths, f.name, column_mappings=mappings)

            with open(f.name) as rf:
                reader = csv.DictReader(rf)
                fieldnames = reader.fieldnames
                data = list(reader)

        assert "INSPOL_STS_TAG" in fieldnames
        assert "INSPOL_COMDTE_C" in fieldnames
        assert data[0]["INSPOL_STS_TAG"] == "E"
        assert data[0]["INSPOL_COMDTE_C"] == "20240301"


# --- Legacy format preserved without mappings ---


class TestLegacyFormatPreserved:
    def test_json_legacy_without_mappings(self):
        params = [Parameter("age", "int")]
        paths = [_make_path(1, leaf_value='"junior"')]
        rows = [_make_row({"age": 10}, path_id=1)]

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            _to_json(rows, params, paths, f.name)

            with open(f.name) as rf:
                data = json.load(rf)

        assert "parameters" in data[0]
        assert data[0]["parameters"]["age"] == 10

    def test_csv_legacy_without_mappings(self):
        params = [Parameter("age", "int")]
        paths = [_make_path(1)]
        rows = [_make_row({"age": 10}, path_id=1)]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            _to_csv(rows, params, paths, f.name)

            with open(f.name) as rf:
                reader = csv.DictReader(rf)
                fieldnames = reader.fieldnames

        assert "age" in fieldnames
        assert "INSPOL_STS_TAG" not in fieldnames


# --- Schema ordering ---


class TestSchemaOrdering:
    def test_schema_reorders_columns(self):
        params = [Parameter("comdteC", "Integer"), Parameter("stsTag", "String")]
        paths = [_make_path(1)]
        rows = [_make_row({"stsTag": "E", "comdteC": 20240301}, path_id=1)]

        mappings = [
            ColumnMapping(
                table_name="T_INSPOL",
                field_to_column={
                    "stsTag": "INSPOL_STS_TAG",
                    "comdteC": "INSPOL_COMDTE_C",
                },
            )
        ]
        schema = [
            SchemaInfo(
                table_name="T_INSPOL",
                column_order=["INSPOL_STS_TAG", "INSPOL_COMDTE_C"],
            )
        ]

        with tempfile.NamedTemporaryFile(suffix=".csv", delete=False) as f:
            _to_csv(rows, params, paths, f.name, column_mappings=mappings, schema=schema)

            with open(f.name) as rf:
                reader = csv.DictReader(rf)
                fieldnames = reader.fieldnames

        # Schema says STS_TAG first, COMDTE_C second
        param_fields = [n for n in fieldnames if n not in ("expected_output", "path_id", "row_type")]
        assert param_fields == ["INSPOL_STS_TAG", "INSPOL_COMDTE_C"]


# --- build_column_mappings and load_schema_from_csv ---


class TestBuildColumnMappings:
    def test_scans_entity_files(self, tmp_path):
        entity_file = tmp_path / "INSPOL.java"
        entity_file.write_text(ENTITY_JAVA)

        mappings = build_column_mappings(tmp_path)

        assert len(mappings) == 1
        assert mappings[0].table_name == "T_INSPOL"
        assert mappings[0].field_to_column["stsTag"] == "INSPOL_STS_TAG"

    def test_skips_files_without_table(self, tmp_path):
        entity_file = tmp_path / "PlainClass.java"
        entity_file.write_text(ENTITY_NO_TABLE)

        mappings = build_column_mappings(tmp_path)

        assert len(mappings) == 0

    def test_empty_directory(self, tmp_path):
        mappings = build_column_mappings(tmp_path)
        assert mappings == []


class TestLoadSchemaFromCSV:
    def test_reads_csv_headers(self, tmp_path):
        csv_file = tmp_path / "T_INSPOL.csv"
        csv_file.write_text("INSPOL_STS_TAG,INSPOL_COMDTE_C\nE,20240301\n")

        schemas = load_schema_from_csv(tmp_path)

        assert len(schemas) == 1
        assert schemas[0].table_name == "T_INSPOL"
        assert schemas[0].column_order == ["INSPOL_STS_TAG", "INSPOL_COMDTE_C"]
        assert len(schemas[0].sample_values) == 1
        assert schemas[0].sample_values[0]["INSPOL_STS_TAG"] == "E"

    def test_ignores_non_table_csvs(self, tmp_path):
        csv_file = tmp_path / "random.csv"
        csv_file.write_text("a,b\n1,2\n")

        schemas = load_schema_from_csv(tmp_path)
        assert schemas == []

    def test_empty_directory(self, tmp_path):
        schemas = load_schema_from_csv(tmp_path)
        assert schemas == []


# --- assemble() with column mappings ---


class TestAssembleWithMappings:
    def test_assemble_json_flat(self):
        params = [Parameter("stsTag", "String")]
        paths = [_make_path(1, leaf_value='"result"')]
        rows = [_make_row({"stsTag": "E"}, path_id=1)]

        mappings = [
            ColumnMapping(
                table_name="T_INSPOL",
                field_to_column={"stsTag": "INSPOL_STS_TAG"},
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                rows, [], [], paths, params,
                format="json",
                output_path=f"{tmpdir}/out.json",
                column_mappings=mappings,
            )

            with open(out) as f:
                data = json.load(f)

        assert "parameters" not in data[0]
        assert data[0]["INSPOL_STS_TAG"] == "E"

    def test_assemble_csv_flat(self):
        params = [Parameter("stsTag", "String")]
        paths = [_make_path(1)]
        rows = [_make_row({"stsTag": "E"}, path_id=1)]

        mappings = [
            ColumnMapping(
                table_name="T_INSPOL",
                field_to_column={"stsTag": "INSPOL_STS_TAG"},
            )
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                rows, [], [], paths, params,
                format="csv",
                output_path=f"{tmpdir}/out.csv",
                column_mappings=mappings,
            )

            with open(out) as f:
                reader = csv.DictReader(f)
                fieldnames = reader.fieldnames

        assert "INSPOL_STS_TAG" in fieldnames

    def test_assemble_no_mappings_preserves_legacy(self):
        params = [Parameter("age", "int")]
        paths = [_make_path(1, leaf_value='"junior"')]
        rows = [_make_row({"age": 10}, path_id=1)]

        with tempfile.TemporaryDirectory() as tmpdir:
            out = assemble(
                rows, [], [], paths, params,
                format="json",
                output_path=f"{tmpdir}/out.json",
            )

            with open(out) as f:
                data = json.load(f)

        assert "parameters" in data[0]
        assert data[0]["parameters"]["age"] == 10
