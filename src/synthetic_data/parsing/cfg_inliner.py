"""CFG-level inlining of same-class method calls.

For a given entry method, replaces StatementNodes containing same-class calls
with cloned callee CFGs, so that all downstream phases (condition extraction,
path enumeration, Z3 solving) work unchanged on the enriched CFG.
"""

from __future__ import annotations

import itertools

from synthetic_data.models.call_graph import CallGraph, CallSite
from synthetic_data.models.cfg_node import (
    CFG,
    CFGNode,
    AssignmentNode,
    DecisionNode,
    EntryNode,
    FieldInfo,
    LeafNode,
    StatementNode,
)


def inline_calls(
    caller_cfg: CFG,
    call_graph: CallGraph,
    cfg_registry: dict[str, CFG],
    source: bytes,
    fields: list[FieldInfo] | None = None,
    max_depth: int = 2,
    max_paths: int = 256,
) -> CFG:
    """Inline same-class callee CFGs into the caller's CFG.

    Each callee's CFG is cloned with fresh node IDs and spliced into the
    caller at each call site.

    Args:
        caller_cfg: The CFG to inline calls into.
        call_graph: Same-class call graph.
        cfg_registry: Map of method name -> CFG for all class methods.
        source: Java source bytes for AST text extraction.
        fields: Instance field declarations (for detecting field side effects).
        max_depth: Maximum inlining depth.
        max_paths: Maximum paths limit.

    Returns:
        A new CFG with callee CFGs inlined at call sites.
    """
    if fields is None:
        fields = []

    caller_name = caller_cfg.method_info.name if caller_cfg.method_info else ""
    field_names = {f.name for f in fields}
    field_types = {f.name: f.java_type for f in fields}

    call_sites = call_graph.callees_of(caller_name)
    if not call_sites:
        return caller_cfg

    # Clone caller CFG (without tree-sitter nodes which aren't picklable)
    cfg = _clone_cfg(caller_cfg)

    max_id = max((n.id for n in cfg.nodes), default=0)
    counter = itertools.count(max_id + 1)

    if max_depth > 0:
        _inline_into_cfg(
            cfg, call_sites, call_graph, cfg_registry, source,
            field_names, field_types, counter, depth=0,
            max_depth=max_depth, max_paths=max_paths,
        )

    return cfg


# ── Manual CFG cloning (tree-sitter nodes are not picklable) ──────────────


def _clone_cfg(cfg: CFG) -> CFG:
    """Clone a CFG without deepcopy, preserving node identity within the clone."""
    cloned_map: dict[int, CFGNode] = {}
    cloned_nodes: list[CFGNode] = []

    # First pass: create clones
    for orig in cfg.nodes:
        clone = _clone_node(orig)
        cloned_map[orig.id] = clone
        cloned_nodes.append(clone)

    # Second pass: rewire edges
    _rewire_cloned_edges(cfg.nodes, cloned_map)

    cloned_entry = cloned_map[cfg.entry.id]
    return CFG(
        entry=cloned_entry,
        nodes=cloned_nodes,
        method_info=cfg.method_info,  # shared reference is fine
    )


def _clone_node(orig: CFGNode) -> CFGNode:
    """Create a shallow clone of a CFG node, preserving id and scalar fields."""
    if isinstance(orig, EntryNode):
        return EntryNode(id=orig.id, successors=[])
    elif isinstance(orig, DecisionNode):
        return DecisionNode(
            id=orig.id,
            condition_expr=orig.condition_expr,
            condition_ast=orig.condition_ast,  # tree-sitter ref — kept as-is
            true_branch=None,
            false_branch=None,
        )
    elif isinstance(orig, StatementNode):
        return StatementNode(
            id=orig.id,
            code=orig.code,
            successors=[],
            ast_node=orig.ast_node,  # tree-sitter ref — kept as-is
        )
    elif isinstance(orig, AssignmentNode):
        return AssignmentNode(
            id=orig.id,
            target=orig.target,
            value_expr=orig.value_expr,
            java_type=orig.java_type,
            successors=[],
        )
    elif isinstance(orig, LeafNode):
        return LeafNode(
            id=orig.id,
            leaf_type=orig.leaf_type,
            value_expr=orig.value_expr,
        )
    else:
        # Unknown node type — basic clone
        return CFGNode(id=orig.id, node_type=orig.node_type)


def _rewire_cloned_edges(originals: list[CFGNode], cloned_map: dict[int, CFGNode]):
    """Rewire edges in cloned nodes to point to other cloned nodes."""
    for orig in originals:
        clone = cloned_map[orig.id]

        if isinstance(orig, EntryNode) and isinstance(clone, EntryNode):
            clone.successors = [
                cloned_map[s.id] for s in orig.successors if s.id in cloned_map
            ]

        elif isinstance(orig, DecisionNode) and isinstance(clone, DecisionNode):
            if orig.true_branch and orig.true_branch.id in cloned_map:
                clone.true_branch = cloned_map[orig.true_branch.id]
            if orig.false_branch and orig.false_branch.id in cloned_map:
                clone.false_branch = cloned_map[orig.false_branch.id]

        elif isinstance(orig, StatementNode) and isinstance(clone, StatementNode):
            clone.successors = [
                cloned_map[s.id] for s in orig.successors if s.id in cloned_map
            ]

        elif isinstance(orig, AssignmentNode) and isinstance(clone, AssignmentNode):
            clone.successors = [
                cloned_map[s.id] for s in orig.successors if s.id in cloned_map
            ]


# ── Inlining logic ───────────────────────────────────────────────────────


def _inline_into_cfg(
    cfg: CFG,
    call_sites: list[CallSite],
    call_graph: CallGraph,
    cfg_registry: dict[str, CFG],
    source: bytes,
    field_names: set[str],
    field_types: dict[str, str],
    counter: itertools.count,
    depth: int,
    max_depth: int,
    max_paths: int,
):
    """Walk the CFG and inline callees at matching StatementNodes."""
    site_by_callee: dict[str, CallSite] = {}
    for cs in call_sites:
        site_by_callee[cs.callee_method] = cs

    nodes_to_inline: list[tuple[StatementNode, CallSite]] = []
    for node in list(cfg.nodes):
        if isinstance(node, StatementNode) and node.ast_node is not None:
            call_site = _find_call_in_statement(node, source, site_by_callee)
            if call_site is not None:
                nodes_to_inline.append((node, call_site))

    for stmt_node, call_site in nodes_to_inline:
        callee_name = call_site.callee_method
        if callee_name not in cfg_registry:
            continue

        callee_cfg = cfg_registry[callee_name]

        cloned_entry, cloned_nodes, cloned_leaves = _clone_callee_cfg(
            callee_cfg, counter, call_site.result_variable,
            field_names, field_types,
        )

        cfg.nodes.extend(cloned_nodes)
        _splice_at_statement(cfg, stmt_node, cloned_entry, cloned_leaves)

        if depth + 1 < max_depth:
            nested_sites = call_graph.callees_of(callee_name)
            if nested_sites:
                _inline_into_cfg(
                    cfg, nested_sites, call_graph, cfg_registry, source,
                    field_names, field_types, counter,
                    depth=depth + 1, max_depth=max_depth, max_paths=max_paths,
                )


def _find_call_in_statement(
    stmt: StatementNode,
    source: bytes,
    site_by_callee: dict[str, CallSite],
) -> CallSite | None:
    """Check if a StatementNode's AST contains a same-class method call."""
    if stmt.ast_node is None:
        return None
    return _search_for_call(stmt.ast_node, source, site_by_callee)


def _search_for_call(
    node, source: bytes, site_by_callee: dict[str, CallSite]
) -> CallSite | None:
    """Recursively search an AST subtree for a matching method invocation."""
    if node.type == "method_invocation":
        name_node = node.child_by_field_name("name")
        if name_node is not None:
            callee = source[name_node.start_byte:name_node.end_byte].decode("utf-8")
            if callee in site_by_callee:
                return site_by_callee[callee]

    for child in node.children:
        result = _search_for_call(child, source, site_by_callee)
        if result is not None:
            return result
    return None


def _clone_callee_cfg(
    callee_cfg: CFG,
    counter: itertools.count,
    result_variable: str | None,
    field_names: set[str],
    field_types: dict[str, str],
) -> tuple[EntryNode, list[CFGNode], list[CFGNode]]:
    """Clone a callee's CFG with fresh node IDs.

    - Replaces LeafNodes with AssignmentNodes when there's a result variable.
    - Detects field assignments (this.field = value) in StatementNodes
      and converts them to AssignmentNodes.

    Returns (cloned_entry, all_cloned_nodes, leaf_or_assignment_nodes).
    """
    cloned_nodes: list[CFGNode] = []
    leaves: list[CFGNode] = []
    cloned_map: dict[int, CFGNode] = {}

    # First pass: create clones with fresh IDs
    for orig in callee_cfg.nodes:
        new_id = next(counter)
        clone = _clone_node(orig)
        clone.id = new_id
        cloned_map[orig.id] = clone
        cloned_nodes.append(clone)

    # Second pass: rewire edges using cloned_map
    _rewire_cloned_edges(callee_cfg.nodes, cloned_map)

    # Third pass: transform nodes (field assignments, return values)
    for orig in callee_cfg.nodes:
        clone = cloned_map[orig.id]

        if isinstance(clone, StatementNode):
            field_assign = _detect_field_assignment(clone, field_names, field_types)
            if field_assign is not None:
                assign = AssignmentNode(
                    id=clone.id,
                    target=field_assign[0],
                    value_expr=field_assign[1],
                    java_type=field_assign[2],
                    successors=list(clone.successors),
                )
                cloned_map[orig.id] = assign
                idx = cloned_nodes.index(clone)
                cloned_nodes[idx] = assign
                _rewire_references(cloned_nodes, clone, assign)

        elif isinstance(clone, LeafNode):
            if result_variable is not None and clone.leaf_type == "return":
                assign = AssignmentNode(
                    id=clone.id,
                    target=result_variable,
                    value_expr=clone.value_expr,
                    java_type="",
                    successors=[],
                )
                cloned_map[orig.id] = assign
                idx = cloned_nodes.index(clone)
                cloned_nodes[idx] = assign
                _rewire_references(cloned_nodes, clone, assign)
                leaves.append(assign)
            elif clone.leaf_type == "throw":
                leaves.append(clone)
            else:
                # void return or end — pass-through
                assign = AssignmentNode(
                    id=clone.id,
                    target="",
                    value_expr=None,
                    java_type="",
                    successors=[],
                )
                cloned_map[orig.id] = assign
                idx = cloned_nodes.index(clone)
                cloned_nodes[idx] = assign
                _rewire_references(cloned_nodes, clone, assign)
                leaves.append(assign)

    cloned_entry = cloned_map[callee_cfg.entry.id]
    return cloned_entry, cloned_nodes, leaves


def _detect_field_assignment(
    stmt: StatementNode,
    field_names: set[str],
    field_types: dict[str, str],
) -> tuple[str, str, str] | None:
    """Detect ``this.field = value`` patterns in a statement's code.

    Returns (field_name, value_expr, java_type) or None.
    """
    code = stmt.code.strip().rstrip(";").strip()

    if not code.startswith("this."):
        return None

    eq_idx = code.find("=")
    if eq_idx < 0:
        return None
    # Exclude ==, !=, <=, >=
    if eq_idx + 1 < len(code) and code[eq_idx + 1] == "=":
        return None
    if eq_idx > 0 and code[eq_idx - 1] in ("!", "<", ">"):
        return None

    lhs = code[:eq_idx].strip()
    rhs = code[eq_idx + 1:].strip()

    if not lhs.startswith("this."):
        return None

    field_name = lhs[5:]
    if field_name not in field_names:
        return None

    java_type = field_types.get(field_name, "")
    return (field_name, rhs, java_type)


def _rewire_references(nodes: list[CFGNode], old: CFGNode, new: CFGNode):
    """Replace references to old node with new node in all nodes."""
    for node in nodes:
        if node is new:
            continue
        if isinstance(node, EntryNode):
            node.successors = [new if s is old else s for s in node.successors]
        elif isinstance(node, DecisionNode):
            if node.true_branch is old:
                node.true_branch = new
            if node.false_branch is old:
                node.false_branch = new
        elif isinstance(node, StatementNode):
            node.successors = [new if s is old else s for s in node.successors]
        elif isinstance(node, AssignmentNode):
            node.successors = [new if s is old else s for s in node.successors]


def _splice_at_statement(
    cfg: CFG,
    stmt_node: StatementNode,
    callee_entry: EntryNode,
    callee_leaves: list[CFGNode],
):
    """Splice the callee's CFG in place of a StatementNode.

    Predecessors of stmt_node -> callee entry's successors
    Callee leaves -> stmt_node's original successors
    """
    original_successors = list(stmt_node.successors)

    for leaf in callee_leaves:
        if isinstance(leaf, LeafNode):
            continue  # throw — leave as terminal
        if isinstance(leaf, AssignmentNode):
            leaf.successors = list(original_successors)

    callee_first_nodes = callee_entry.successors if callee_entry.successors else []
    if not callee_first_nodes:
        return

    for node in cfg.nodes:
        if node is stmt_node:
            continue
        _replace_successor(node, stmt_node, callee_first_nodes)

    if cfg.entry is not stmt_node:
        _replace_successor(cfg.entry, stmt_node, callee_first_nodes)

    if stmt_node in cfg.nodes:
        cfg.nodes.remove(stmt_node)


def _replace_successor(
    node: CFGNode, old: CFGNode, replacements: list[CFGNode]
):
    """Replace old with replacement(s) in node's successor references."""
    if isinstance(node, EntryNode):
        new_succs = []
        for s in node.successors:
            if s is old:
                new_succs.extend(replacements)
            else:
                new_succs.append(s)
        node.successors = new_succs

    elif isinstance(node, DecisionNode):
        if node.true_branch is old:
            node.true_branch = replacements[0] if replacements else None
        if node.false_branch is old:
            node.false_branch = replacements[0] if replacements else None

    elif isinstance(node, StatementNode):
        new_succs = []
        for s in node.successors:
            if s is old:
                new_succs.extend(replacements)
            else:
                new_succs.append(s)
        node.successors = new_succs

    elif isinstance(node, AssignmentNode):
        new_succs = []
        for s in node.successors:
            if s is old:
                new_succs.extend(replacements)
            else:
                new_succs.append(s)
        node.successors = new_succs
