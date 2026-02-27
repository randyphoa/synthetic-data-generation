"""Column mapping models for database-aligned output format."""

from __future__ import annotations

import csv
from dataclasses import dataclass, field
from pathlib import Path

from synthetic_data.parsing.java_parser import (
    extract_column_annotations,
    extract_table_name,
    parse_file,
)


@dataclass
class ColumnMapping:
    """Maps Java field names to SQL column names for a single entity/table."""

    table_name: str
    field_to_column: dict[str, str] = field(default_factory=dict)

    def resolve(self, param_name: str) -> str | None:
        """Resolve a parameter name to its SQL column name.

        Handles:
        - Direct field names: "stsTag" → lookup directly
        - Flattened getters:  "inspol__comdteC" → split on "__" → lookup "comdteC"
        - Dot getter calls:   "inspol.getComdteC()" → extract "comdteC" → lookup
        """
        # Direct lookup
        if param_name in self.field_to_column:
            return self.field_to_column[param_name]

        # Flattened getter: prefix__fieldName
        if "__" in param_name:
            _, field_name = param_name.split("__", 1)
            if field_name in self.field_to_column:
                return self.field_to_column[field_name]

        # Dot getter call: obj.getFieldName() → fieldName
        if "." in param_name:
            suffix = param_name.rsplit(".", 1)[1]
            field_name = _getter_to_field(suffix)
            if field_name and field_name in self.field_to_column:
                return self.field_to_column[field_name]

        return None


def _getter_to_field(getter: str) -> str | None:
    """Convert a getter method name to its field name.

    "getComdteC()" → "comdteC"
    "getStsTag()"  → "stsTag"
    "isActive()"   → "active"
    """
    # Strip trailing ()
    name = getter.rstrip("()")
    if name.startswith("get") and len(name) > 3:
        return name[3].lower() + name[4:]
    if name.startswith("is") and len(name) > 2:
        return name[2].lower() + name[3:]
    return None


@dataclass
class SchemaInfo:
    """Schema information loaded from sample CSV files."""

    table_name: str
    column_order: list[str] = field(default_factory=list)
    sample_values: list[dict[str, str]] = field(default_factory=list)


def build_column_mappings(entity_dir: str | Path) -> list[ColumnMapping]:
    """Scan a directory for entity Java files with @Column annotations.

    Returns a list of ColumnMapping objects, one per entity file that has
    @Table and @Column annotations.
    """
    entity_dir = Path(entity_dir)
    mappings: list[ColumnMapping] = []

    for java_file in sorted(entity_dir.glob("*.java")):
        try:
            tree, source = parse_file(str(java_file))
        except Exception:
            continue

        table_name = extract_table_name(tree, source)
        if not table_name:
            continue

        field_to_column = extract_column_annotations(tree, source)
        if not field_to_column:
            continue

        mappings.append(ColumnMapping(table_name=table_name, field_to_column=field_to_column))

    return mappings


def load_schema_from_csv(csv_dir: str | Path) -> list[SchemaInfo]:
    """Read T_*.csv files to get column ordering and sample values.

    Returns a list of SchemaInfo objects.
    """
    csv_dir = Path(csv_dir)
    schemas: list[SchemaInfo] = []

    for csv_file in sorted(csv_dir.glob("T_*.csv")):
        table_name = csv_file.stem  # e.g. "T_INSPOL"

        try:
            with open(csv_file, newline="") as f:
                reader = csv.DictReader(f)
                column_order = list(reader.fieldnames) if reader.fieldnames else []
                sample_values = []
                for i, row in enumerate(reader):
                    if i >= 5:  # Keep at most 5 sample rows
                        break
                    sample_values.append(dict(row))
        except Exception:
            continue

        schemas.append(
            SchemaInfo(
                table_name=table_name,
                column_order=column_order,
                sample_values=sample_values,
            )
        )

    return schemas
