"""Phase 1: Build Control Flow Graphs from method AST nodes."""

from __future__ import annotations

import itertools
from dataclasses import dataclass
from typing import Any

from synthetic_data.models.cfg_node import (
    CFG,
    CFGNode,
    DecisionNode,
    EntryNode,
    LeafNode,
    MethodInfo,
    StatementNode,
)


@dataclass
class _PendingEdge:
    """An edge that needs to be connected to the next CFG node."""

    source: CFGNode
    attr: str
    append: bool = False

    def connect(self, target: CFGNode):
        if self.append:
            getattr(self.source, self.attr).append(target)
        else:
            setattr(self.source, self.attr, target)


def build_cfg(method_info: MethodInfo) -> CFG:
    """Build a control flow graph from a method's tree-sitter AST node."""
    method_node = method_info.node
    counter = itertools.count(1)
    all_nodes: list[CFGNode] = []

    def make(cls, **kwargs):
        node = cls(id=next(counter), **kwargs)
        all_nodes.append(node)
        return node

    entry = make(EntryNode)

    body = _find_body(method_node)
    if body is None:
        end = make(LeafNode, leaf_type="end")
        entry.successors.append(end)
        return CFG(entry=entry, nodes=all_nodes, method_info=method_info)

    stmts = _get_statements(body)
    first, pending = _build_statements(stmts, make)

    if first is not None:
        entry.successors.append(first)

    if pending:
        end = make(LeafNode, leaf_type="end")
        for p in pending:
            p.connect(end)

    return CFG(entry=entry, nodes=all_nodes, method_info=method_info)


def _find_body(method_node) -> Any | None:
    for child in method_node.children:
        if child.type == "block":
            return child
    return None


def _get_statements(block_node) -> list:
    return [c for c in block_node.children if c.type not in ("{", "}")]


def _build_statements(stmts, make) -> tuple[CFGNode | None, list[_PendingEdge]]:
    """Build CFG from a sequence of statements.

    Returns (first_cfg_node, pending_edges).
    """
    first = None
    pending: list[_PendingEdge] = []

    for stmt in stmts:
        cfg_node, node_pending = _build_statement(stmt, make)
        if cfg_node is None:
            continue

        if first is None:
            first = cfg_node

        for p in pending:
            p.connect(cfg_node)

        pending = node_pending

        if not pending:
            break  # terminal (return/throw)

    return first, pending


def _build_statement(stmt, make) -> tuple[CFGNode | None, list[_PendingEdge]]:
    t = stmt.type
    if t == "if_statement":
        return _build_if(stmt, make)
    elif t == "return_statement":
        return _build_return(stmt, make)
    elif t == "throw_statement":
        return _build_throw(stmt, make)
    elif t == "block":
        return _build_statements(_get_statements(stmt), make)
    else:
        return _build_generic(stmt, make)


def _build_if(if_node, make):
    condition_node = if_node.child_by_field_name("condition")
    consequence_node = if_node.child_by_field_name("consequence")
    alternative_node = if_node.child_by_field_name("alternative")

    inner_expr = _unwrap_parens(condition_node)
    condition_text = _node_text(inner_expr) if inner_expr else _node_text(condition_node)

    decision = make(DecisionNode, condition_expr=condition_text, condition_ast=inner_expr)

    # True branch
    true_first, true_pending = _build_statement(consequence_node, make)
    if true_first:
        decision.true_branch = true_first

    # False branch
    if alternative_node:
        false_first, false_pending = _build_statement(alternative_node, make)
        if false_first:
            decision.false_branch = false_first
    else:
        false_pending = [_PendingEdge(decision, "false_branch")]

    return decision, true_pending + false_pending


def _build_return(node, make):
    value_nodes = [c for c in node.children if c.is_named]
    value = _node_text(value_nodes[0]) if value_nodes else None
    leaf = make(LeafNode, leaf_type="return", value_expr=value)
    return leaf, []


def _build_throw(node, make):
    value_nodes = [c for c in node.children if c.is_named]
    value = _node_text(value_nodes[0]) if value_nodes else None
    leaf = make(LeafNode, leaf_type="throw", value_expr=value)
    return leaf, []


def _build_generic(node, make):
    code = _node_text(node)
    stmt = make(StatementNode, code=code, ast_node=node)
    return stmt, [_PendingEdge(stmt, "successors", append=True)]


def _unwrap_parens(node):
    """Unwrap parenthesized_expression to get the inner expression."""
    if node is None:
        return None
    if node.type == "parenthesized_expression":
        named = [c for c in node.children if c.is_named]
        return named[0] if named else node
    return node


def _node_text(node) -> str:
    return node.text.decode()
