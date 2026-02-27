from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class SQLCondition:
    column: str  # e.g., "STATUS"
    operator: str  # e.g., "=", ">=", "IN"
    value: str  # "?" (parameterized) or literal
    dto_field: str  # e.g., "status"


@dataclass
class DAOMethodSQL:
    method: str  # e.g., "findAllByStatus"
    table: str  # e.g., "T_ORDERS"
    conditions: list[SQLCondition] = field(default_factory=list)
    joins: list[dict] = field(default_factory=list)
    hardcoded_values: list[dict] = field(default_factory=list)
