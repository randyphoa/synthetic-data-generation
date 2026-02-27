"""Registry mapping known Java utility methods to Z3-solvable operators."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class UtilityMethodSpec:
    """Describes how a utility method maps to a comparison operator."""

    operator: str  # e.g., "==", ">", ">="
    arg_count: int  # 1 or 2
    result_type: str  # Java type hint for arguments, e.g., "Integer", "String"
    default_value: Any = None  # For 1-arg methods: the implicit RHS value


# Global registry: (class_name, method_name) → UtilityMethodSpec
_REGISTRY: dict[tuple[str, str], UtilityMethodSpec] = {}


def register(class_name: str, method_name: str, spec: UtilityMethodSpec) -> None:
    """Register a utility method mapping."""
    _REGISTRY[(class_name, method_name)] = spec


def lookup(class_name: str, method_name: str) -> UtilityMethodSpec | None:
    """Look up a utility method spec. Returns None if not registered."""
    return _REGISTRY.get((class_name, method_name))


def _register_defaults() -> None:
    """Register the default set of known utility methods."""
    register("ServiceUtil", "isSameTag", UtilityMethodSpec("==", 2, "String"))
    register("MSHUtil", "isEqualsInt", UtilityMethodSpec("==", 2, "Integer"))
    register("MSHUtil", "isGreaterThanInt", UtilityMethodSpec(">", 2, "Integer"))
    register("MSHUtil", "isGreaterThanOrEqualsInt", UtilityMethodSpec(">=", 2, "Integer"))
    register("MSHUtil", "isLesserThanInt", UtilityMethodSpec("<", 2, "Integer"))
    register("ObjectUtils", "isEmpty", UtilityMethodSpec("==", 1, "", None))
    register("CollectionUtils", "isEmpty", UtilityMethodSpec("==", 1, "", None))
    register("ServiceUtil", "isNullOrEmptyString", UtilityMethodSpec("==", 1, "String", None))
    register("StringUtils", "isWhitespace", UtilityMethodSpec("==", 1, "String", " "))
    register("DateTimeUtil", "isZeroDate", UtilityMethodSpec("==", 1, "Integer", 0))
    register("DateTimeUtil", "isGreaterOrEqualsDate", UtilityMethodSpec(">=", 2, "Integer"))
    register("DateTimeUtil", "isLessOrEqualsDate", UtilityMethodSpec("<=", 2, "Integer"))


# Auto-register defaults on import
_register_defaults()
