"""Phase 4: Assemble generated rows into CSV or JSON output."""

from __future__ import annotations

import csv
import json
from pathlib import Path as FilePath
from typing import Any

from synthetic_data.models.cfg_node import Parameter
from synthetic_data.models.column_mapping import ColumnMapping, SchemaInfo
from synthetic_data.models.condition import Path
from synthetic_data.solving.boundary import DataRow


def assemble(
    path_rows: list[DataRow],
    boundary_rows: list[DataRow],
    edge_rows: list[DataRow],
    paths: list[Path],
    parameters: list[Parameter],
    format: str = "csv",
    output_path: str | None = None,
    column_mappings: list[ColumnMapping] | None = None,
    schema: list[SchemaInfo] | None = None,
) -> str:
    """Assemble all generated rows into a CSV or JSON file.

    When column_mappings is provided, output uses flat records keyed by
    SQL column names instead of nested parameters with Java field names.

    Returns the path to the written file.
    """
    all_rows = _deduplicate(path_rows + boundary_rows + edge_rows)

    if output_path is None:
        output_path = f"dataset.{format}"

    out = FilePath(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)

    if format == "json":
        _to_json(all_rows, parameters, paths, str(out), column_mappings, schema)
    else:
        _to_csv(all_rows, parameters, paths, str(out), column_mappings, schema)

    return str(out)


def build_path_map(rows: list[DataRow], paths: list[Path]) -> list[dict]:
    """Map each row to its path and expected output.

    Returns a list of dicts with parameter values, expected_output,
    path_id, and row_type.
    """
    path_lookup: dict[int, Path] = {p.id: p for p in paths}
    result: list[dict] = []

    for row in rows:
        path = path_lookup.get(row.path_id)
        expected = path.leaf_value if path else None

        entry: dict[str, Any] = {}
        entry.update(row.values)
        entry["expected_output"] = expected
        entry["path_id"] = row.path_id
        entry["row_type"] = row.row_type

        result.append(entry)

    return result


def _to_csv(
    rows: list[DataRow],
    parameters: list[Parameter],
    paths: list[Path],
    output_path: str,
    column_mappings: list[ColumnMapping] | None = None,
    schema: list[SchemaInfo] | None = None,
) -> None:
    """Write rows to a CSV file."""
    mapped = build_path_map(rows, paths)
    param_names = [p.name for p in parameters]

    if column_mappings:
        # Filter to only mapped params, then resolve to SQL column names
        mapped_params = [n for n in param_names if _is_mapped(n, column_mappings)]
        display_names = [
            _resolve_output_name(n, column_mappings) for n in mapped_params
        ]
        # Apply schema column ordering if available
        display_names = _apply_schema_order(display_names, schema)
    else:
        mapped_params = param_names
        display_names = [_format_param_name(n) for n in param_names]

    fieldnames = display_names + ["expected_output", "path_id", "row_type"]

    # Remap internal names → display names in each entry
    for entry in mapped:
        for internal, display in zip(mapped_params, display_names):
            if internal != display and internal in entry:
                entry[display] = entry.pop(internal)

    with open(output_path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for entry in mapped:
            writer.writerow(entry)


def _resolve_output_name(
    param_name: str, column_mappings: list[ColumnMapping]
) -> str:
    """Map a parameter name to its SQL column name via ColumnMapping.resolve().

    Tries each mapping until one resolves. Falls back to the existing
    ``__`` → ``.`` conversion if no mapping matches.
    """
    for mapping in column_mappings:
        resolved = mapping.resolve(param_name)
        if resolved is not None:
            return resolved
    # Fallback: no mapping found
    return _format_param_name(param_name)


def _apply_schema_order(
    display_names: list[str], schema: list[SchemaInfo] | None
) -> list[str]:
    """Reorder display names to match the schema column order when available.

    Columns present in the schema come first (in schema order), followed by
    any remaining columns in their original order.
    """
    if not schema:
        return display_names

    # Collect all schema column orders into one ordered list
    schema_order: list[str] = []
    for s in schema:
        for col in s.column_order:
            if col not in schema_order:
                schema_order.append(col)

    display_set = set(display_names)
    ordered: list[str] = []
    for col in schema_order:
        if col in display_set:
            ordered.append(col)
            display_set.discard(col)

    # Append remaining columns not in schema (preserve original order)
    for name in display_names:
        if name in display_set:
            ordered.append(name)
            display_set.discard(name)

    return ordered


def _is_mapped(param_name: str, column_mappings: list[ColumnMapping]) -> bool:
    """Return True if any mapping resolves this parameter to a SQL column name."""
    return any(m.resolve(param_name) is not None for m in column_mappings)


def _format_param_name(name: str) -> str:
    """Convert flattened param names to readable form: inspol__comdteC → inspol.comdteC."""
    return name.replace("__", ".")


def _to_json(
    rows: list[DataRow],
    parameters: list[Parameter],
    paths: list[Path],
    output_path: str,
    column_mappings: list[ColumnMapping] | None = None,
    schema: list[SchemaInfo] | None = None,
) -> None:
    """Write rows to a JSON file."""
    path_lookup: dict[int, Path] = {p.id: p for p in paths}
    param_names = [p.name for p in parameters]
    result: list[dict] = []

    if column_mappings:
        # Filter to only mapped params, then resolve to SQL column names
        mapped_params = [n for n in param_names if _is_mapped(n, column_mappings)]
        display_names = [
            _resolve_output_name(n, column_mappings) for n in mapped_params
        ]
        display_names = _apply_schema_order(display_names, schema)
        # Build internal→display mapping
        name_map = dict(zip(mapped_params, [
            _resolve_output_name(n, column_mappings) for n in mapped_params
        ]))

        for row in rows:
            path = path_lookup.get(row.path_id)
            expected = path.leaf_value if path else None

            entry: dict[str, Any] = {}
            for display in display_names:
                # Find the internal name for this display name
                internal = next(
                    (k for k, v in name_map.items() if v == display), None
                )
                if internal is not None:
                    entry[display] = row.values.get(internal)
            entry["expected_output"] = expected
            entry["path_id"] = row.path_id
            entry["row_type"] = row.row_type
            result.append(entry)
    else:
        # Legacy nested format
        for row in rows:
            path = path_lookup.get(row.path_id)
            expected = path.leaf_value if path else None

            entry = {
                "parameters": {
                    _format_param_name(name): row.values.get(name)
                    for name in param_names
                },
                "expected_output": expected,
                "path_id": row.path_id,
                "row_type": row.row_type,
            }
            result.append(entry)

    with open(output_path, "w") as f:
        json.dump(result, f, indent=2, default=str)


def _deduplicate(rows: list[DataRow]) -> list[DataRow]:
    """Remove rows with identical (path_id, values) combinations."""
    seen: set[tuple] = set()
    unique: list[DataRow] = []
    for row in rows:
        key = (row.path_id, tuple(sorted(row.values.items())))
        if key not in seen:
            seen.add(key)
            unique.append(row)
    return unique
