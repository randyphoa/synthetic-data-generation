"""Data models for same-class call graph analysis."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CallSite:
    """A single call from one method to another."""

    caller_method: str
    callee_method: str
    call_node: Any = None  # tree-sitter node of the method_invocation
    result_variable: str | None = None  # e.g., "isValid" if `isValid = validate()`
    is_same_class: bool = True


@dataclass
class CallGraph:
    """Same-class call graph for a Java class."""

    class_name: str
    methods: list[str] = field(default_factory=list)
    edges: list[CallSite] = field(default_factory=list)
    adjacency: dict[str, list[CallSite]] = field(default_factory=dict)

    def callees_of(self, method_name: str) -> list[CallSite]:
        """Return all call sites where method_name is the caller."""
        return self.adjacency.get(method_name, [])

    def topological_order(self) -> list[str]:
        """Return methods in bottom-up order (leaf methods first).

        Methods with no outgoing same-class calls come first,
        then their callers, etc. Falls back to original order
        for cycles.
        """
        visited: set[str] = set()
        order: list[str] = []
        in_stack: set[str] = set()

        def visit(m: str):
            if m in visited:
                return
            if m in in_stack:
                return  # cycle — skip
            in_stack.add(m)
            for cs in self.callees_of(m):
                if cs.callee_method in self.adjacency or cs.callee_method in visited:
                    visit(cs.callee_method)
            in_stack.discard(m)
            visited.add(m)
            order.append(m)

        for m in self.methods:
            visit(m)

        return order
