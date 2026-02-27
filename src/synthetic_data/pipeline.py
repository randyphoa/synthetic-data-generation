"""Pipeline: orchestrate Phase 1 → 2 → 3 → 4 for a Java source file."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from synthetic_data.extraction.path_enumerator import enumerate_paths
from synthetic_data.generation.dataset import assemble, build_path_map
from synthetic_data.models.cfg_node import CFG, MethodInfo, Parameter
from synthetic_data.models.column_mapping import (
    ColumnMapping,
    SchemaInfo,
    build_column_mappings,
    load_schema_from_csv,
)
from synthetic_data.models.condition import Path
from synthetic_data.parsing.call_graph_builder import build_call_graph
from synthetic_data.parsing.cfg import build_cfg
from synthetic_data.parsing.cfg_inliner import inline_calls
from synthetic_data.parsing.java_parser import (
    extract_class_name,
    extract_constructor_field_map,
    extract_constructors,
    extract_fields,
    extract_methods,
    parse_file,
)
from synthetic_data.solving.boundary import DataRow, generate_boundary_rows, generate_edge_case_rows
from synthetic_data.solving.z3_solver import SolverResult, solve_paths


@dataclass
class MethodResult:
    """Result of running the pipeline on a single method."""

    method_name: str
    parameters: list[Parameter]
    paths: list[Path]
    solver_results: list[SolverResult]
    path_rows: list[DataRow]
    boundary_rows: list[DataRow]
    edge_rows: list[DataRow]
    unreachable_paths: list[Path]


@dataclass
class PipelineResult:
    """Result of running the pipeline on a Java source file."""

    source_file: str
    method_results: list[MethodResult]
    output_file: str | None = None


def run(
    source_file: str,
    *,
    method_name: str | None = None,
    output_format: str = "csv",
    output_path: str | None = None,
    include_boundary: bool = True,
    include_edge_cases: bool = True,
    enable_call_chain: bool = False,
    inline_depth: int = 2,
    max_paths: int = 256,
    entity_dir: str | None = None,
    schema_dir: str | None = None,
) -> PipelineResult:
    """Run the full pipeline on a Java source file.

    Args:
        source_file: Path to the .java file.
        method_name: If set, only analyze this method.
        output_format: "csv" or "json".
        output_path: Where to write the output file.
        include_boundary: Generate boundary value rows.
        include_edge_cases: Generate edge case rows.
        enable_call_chain: Inline same-class callee CFGs for inter-procedural analysis.
        inline_depth: Maximum inlining depth (default 2).
        max_paths: Maximum paths before stopping inlining (default 256).
        entity_dir: Path to directory with entity Java files (@Column annotations).
        schema_dir: Path to directory with sample T_*.csv files for column ordering.

    Returns:
        PipelineResult with per-method details and the output file path.
    """
    # Phase 1: Parse
    tree, source = parse_file(source_file)
    methods = extract_methods(tree, source)

    # Enhancement 2: Extract constructors and build field→param type map
    constructors = extract_constructors(tree, source)
    field_map = extract_constructor_field_map(tree, source)
    constructor_virtual_params = _build_constructor_virtual_params(constructors, field_map)

    # Build call chain infrastructure if enabled
    call_graph = None
    cfg_registry: dict[str, CFG] = {}
    fields = []
    if enable_call_chain:
        class_name = extract_class_name(tree, source)
        fields = extract_fields(tree, source)
        all_methods = list(methods)  # keep full list for call graph
        call_graph = build_call_graph(all_methods, source, class_name)

        # Build CFGs for ALL methods upfront into a registry
        for m in all_methods:
            cfg = build_cfg(m)
            cfg_registry[m.name] = cfg

    if method_name:
        methods = [m for m in methods if m.name == method_name]

    if not methods:
        print(f"No methods found in {source_file}" + (f" matching '{method_name}'" if method_name else ""))
        return PipelineResult(source_file=source_file, method_results=[])

    all_method_results: list[MethodResult] = []
    all_path_rows: list[DataRow] = []
    all_boundary_rows: list[DataRow] = []
    all_edge_rows: list[DataRow] = []
    all_paths: list[Path] = []
    all_parameters: list[Parameter] = []

    for method in methods:
        result = _run_method(
            method, include_boundary, include_edge_cases,
            call_graph=call_graph, cfg_registry=cfg_registry,
            fields=fields, source=source,
            inline_depth=inline_depth, max_paths=max_paths,
            constructor_virtual_params=constructor_virtual_params,
        )
        if result is None:
            continue
        all_method_results.append(result)
        all_path_rows.extend(result.path_rows)
        all_boundary_rows.extend(result.boundary_rows)
        all_edge_rows.extend(result.edge_rows)
        all_paths.extend(result.paths)
        # Track all unique parameters across methods
        seen = {p.name for p in all_parameters}
        for p in result.parameters:
            if p.name not in seen:
                all_parameters.append(p)
                seen.add(p.name)

    # Build column mappings from entity files if directory provided
    column_mappings: list[ColumnMapping] | None = None
    schemas: list[SchemaInfo] | None = None

    if entity_dir:
        column_mappings = build_column_mappings(entity_dir) or None
    elif schema_dir:
        # If no explicit entity dir but schema dir given, try the source file's directory
        from pathlib import Path as _P
        source_parent = _P(source_file).parent
        column_mappings = build_column_mappings(source_parent) or None

    if schema_dir:
        schemas = load_schema_from_csv(schema_dir) or None

    # Phase 4: Assemble
    output_file = None
    if all_path_rows or all_boundary_rows or all_edge_rows:
        output_file = assemble(
            path_rows=all_path_rows,
            boundary_rows=all_boundary_rows,
            edge_rows=all_edge_rows,
            paths=all_paths,
            parameters=all_parameters,
            format=output_format,
            output_path=output_path,
            column_mappings=column_mappings,
            schema=schemas,
        )

    pipeline_result = PipelineResult(
        source_file=source_file,
        method_results=all_method_results,
        output_file=output_file,
    )

    _print_summary(pipeline_result)
    return pipeline_result


def _run_method(
    method: MethodInfo,
    include_boundary: bool,
    include_edge_cases: bool,
    call_graph=None,
    cfg_registry: dict[str, CFG] | None = None,
    fields=None,
    source: bytes | None = None,
    inline_depth: int = 2,
    max_paths: int = 256,
    constructor_virtual_params: dict[str, Parameter] | None = None,
) -> MethodResult | None:
    """Run phases 1b–3 on a single method."""
    params = list(method.parameters)

    # Enhancement 2: If method has no params, try constructor virtual params
    if not params and constructor_virtual_params and source is not None:
        virtual = _find_used_virtual_params(method, constructor_virtual_params, source)
        if virtual:
            params = virtual

    if not params:
        return None

    # Phase 1b: Build CFG
    if cfg_registry and method.name in cfg_registry:
        cfg = cfg_registry[method.name]
    else:
        cfg = build_cfg(method)

    # Phase 1c: Inline callee CFGs if call chain is enabled
    if call_graph is not None and cfg_registry is not None and source is not None:
        cfg = inline_calls(
            caller_cfg=cfg,
            call_graph=call_graph,
            cfg_registry=cfg_registry,
            source=source,
            fields=fields,
            max_depth=inline_depth,
            max_paths=max_paths,
        )

    # Phase 2: Extract paths
    paths = enumerate_paths(cfg, params)
    if not paths:
        return None

    # Enhancement 3: Collect synthetic params discovered during condition extraction
    # (e.g., from getter flattening: inspol__comdteC)
    synthetic = _collect_synthetic_params(paths, params)
    if synthetic:
        params = list(params) + synthetic

    # Phase 3: Solve
    solver_results = solve_paths(paths, params)

    # Build path rows from solver results
    path_rows: list[DataRow] = []
    for sr in solver_results:
        if sr.satisfiable and sr.values:
            path_rows.append(
                DataRow(
                    values=sr.values,
                    path_id=sr.path_id,
                    row_type="path",
                    source=f"path {sr.path_id}",
                )
            )

    # Phase 3b: Boundary and edge cases
    boundary_rows: list[DataRow] = []
    edge_rows: list[DataRow] = []

    reachable_paths = [p for p in paths if p.is_reachable]
    if include_boundary:
        boundary_rows = generate_boundary_rows(reachable_paths, params)
    if include_edge_cases:
        edge_rows = generate_edge_case_rows(reachable_paths, params)

    unreachable = [p for p in paths if not p.is_reachable]

    return MethodResult(
        method_name=method.name,
        parameters=params,
        paths=paths,
        solver_results=solver_results,
        path_rows=path_rows,
        boundary_rows=boundary_rows,
        edge_rows=edge_rows,
        unreachable_paths=unreachable,
    )


def _build_constructor_virtual_params(
    constructors: list[MethodInfo], field_map: dict[str, str]
) -> dict[str, Parameter]:
    """Build a mapping of field name → Parameter from constructor info.

    The field name is used as the parameter name (since that's what the
    method body references), and the java_type comes from the constructor
    parameter's type.
    """
    # Build param_name → java_type from all constructors
    param_type_map: dict[str, str] = {}
    for ctor in constructors:
        for p in ctor.parameters:
            param_type_map[p.name] = p.java_type

    virtual: dict[str, Parameter] = {}
    for field_name, param_name in field_map.items():
        java_type = param_type_map.get(param_name, "")
        if java_type:
            virtual[field_name] = Parameter(name=field_name, java_type=java_type)

    return virtual


def _find_used_virtual_params(
    method: MethodInfo,
    virtual_params: dict[str, Parameter],
    source: bytes,
) -> list[Parameter]:
    """Find virtual params (constructor fields) actually referenced in the method body."""
    if method.node is None:
        return []

    method_text = source[method.node.start_byte : method.node.end_byte].decode("utf-8")
    used: list[Parameter] = []
    for field_name, param in virtual_params.items():
        if field_name in method_text:
            used.append(param)
    return used


def _collect_synthetic_params(
    paths: list[Path], existing_params: list[Parameter]
) -> list[Parameter]:
    """Scan path constraints for variables not in existing params that are Z3-solvable.

    These arise from getter flattening (e.g., inspol__comdteC).
    """
    existing_names = {p.name for p in existing_params}
    discovered: dict[str, str] = {}  # name → java_type

    for path in paths:
        for constraint in path.constraints:
            cond = constraint.condition
            if cond.solver == "z3" and cond.variable and cond.variable not in existing_names:
                if cond.variable not in discovered:
                    discovered[cond.variable] = cond.java_type

    return [Parameter(name=n, java_type=t) for n, t in discovered.items()]


def _print_summary(result: PipelineResult) -> None:
    """Print a human-readable summary of the pipeline results."""
    print(f"\n{'=' * 60}")
    print(f"Source: {result.source_file}")
    print(f"{'=' * 60}")

    total_paths = 0
    total_reachable = 0
    total_unreachable = 0
    total_path_rows = 0
    total_boundary_rows = 0
    total_edge_rows = 0

    for mr in result.method_results:
        reachable = [p for p in mr.paths if p.is_reachable]
        unreachable = mr.unreachable_paths

        total_paths += len(mr.paths)
        total_reachable += len(reachable)
        total_unreachable += len(unreachable)
        total_path_rows += len(mr.path_rows)
        total_boundary_rows += len(mr.boundary_rows)
        total_edge_rows += len(mr.edge_rows)

        param_str = ", ".join(f"{p.java_type} {p.name}" for p in mr.parameters)
        print(f"\n  Method: {mr.method_name}({param_str})")
        print(f"    Paths: {len(reachable)} reachable, {len(unreachable)} unreachable")
        print(f"    Rows:  {len(mr.path_rows)} path, {len(mr.boundary_rows)} boundary, {len(mr.edge_rows)} edge case")

        if unreachable:
            for p in unreachable:
                constraints_str = ", ".join(
                    f"{'!' if c.negated else ''}{c.condition.source_expr}" for c in p.constraints
                )
                print(f"    [dead code] Path {p.id}: {constraints_str}")

    total_rows = total_path_rows + total_boundary_rows + total_edge_rows
    print(f"\n{'─' * 60}")
    print(f"  Total: {len(result.method_results)} methods, {total_paths} paths ({total_reachable} reachable, {total_unreachable} dead)")
    print(f"  Rows:  {total_rows} total ({total_path_rows} path + {total_boundary_rows} boundary + {total_edge_rows} edge)")

    if result.output_file:
        print(f"  Output: {result.output_file}")

    print()
