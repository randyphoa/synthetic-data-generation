from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class Condition:
    """An atomic condition extracted from a decision node."""

    variable: str  # e.g., "age"
    operator: str  # e.g., ">", "==", "startsWith"
    value: Any  # e.g., 18, "Dr", True
    java_type: str  # e.g., "int", "String"
    source_expr: str  # original expression text
    solver: str  # "z3" or "llm"


@dataclass
class Constraint:
    """A condition along a path, possibly negated (false-branch)."""

    condition: Condition
    negated: bool = False


@dataclass
class Path:
    """An entry-to-leaf path through the CFG with its constraint set."""

    id: int
    constraints: list[Constraint]
    leaf_type: str  # "return", "throw", "end"
    leaf_value: str | None = None
    is_reachable: bool = True


# --- Condition expression tree (for logical decomposition) ---


@dataclass
class ConditionExpr:
    """Base class for condition expression tree nodes."""

    pass


@dataclass
class AtomicExpr(ConditionExpr):
    condition: Condition


@dataclass
class AndExpr(ConditionExpr):
    left: ConditionExpr
    right: ConditionExpr


@dataclass
class OrExpr(ConditionExpr):
    left: ConditionExpr
    right: ConditionExpr


@dataclass
class NotExpr(ConditionExpr):
    operand: ConditionExpr
