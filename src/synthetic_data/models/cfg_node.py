from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Parameter:
    name: str
    java_type: str


@dataclass
class MethodInfo:
    name: str
    parameters: list[Parameter]
    return_type: str | None = None
    node: Any = None  # tree-sitter AST node


@dataclass
class CFGNode:
    id: int
    node_type: str = ""


@dataclass
class EntryNode(CFGNode):
    successors: list[CFGNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = "entry"


@dataclass
class DecisionNode(CFGNode):
    condition_expr: str = ""
    condition_ast: Any = None  # tree-sitter node for the condition expression
    true_branch: CFGNode | None = None
    false_branch: CFGNode | None = None

    def __post_init__(self):
        self.node_type = "decision"


@dataclass
class StatementNode(CFGNode):
    code: str = ""
    successors: list[CFGNode] = field(default_factory=list)
    ast_node: Any = None  # tree-sitter node for call-site detection

    def __post_init__(self):
        self.node_type = "statement"


@dataclass
class AssignmentNode(CFGNode):
    """Synthetic node representing a value assignment (from inlined callee)."""

    target: str = ""
    value_expr: str | None = None
    java_type: str = ""
    successors: list[CFGNode] = field(default_factory=list)

    def __post_init__(self):
        self.node_type = "assignment"


@dataclass
class LeafNode(CFGNode):
    leaf_type: str = ""  # "return", "throw", "end"
    value_expr: str | None = None

    def __post_init__(self):
        self.node_type = "leaf"


@dataclass
class FieldInfo:
    """Instance field declaration from a Java class."""

    name: str
    java_type: str


@dataclass
class CFG:
    entry: EntryNode
    nodes: list[CFGNode] = field(default_factory=list)
    method_info: MethodInfo | None = None
