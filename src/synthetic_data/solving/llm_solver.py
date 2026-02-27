"""Phase 3: LLM fallback solver for constraints that Z3 cannot handle."""

from __future__ import annotations

import logging
from typing import Any

from synthetic_data.llm.client import call_llm_json, call_llm_json_batch
from synthetic_data.llm.prompts import (
    CONSTRAINT_SOLVING_PROMPT,
    CONSTRAINT_SOLVING_SYSTEM,
)
from synthetic_data.models.cfg_node import MethodInfo, Parameter
from synthetic_data.models.condition import Constraint

logger = logging.getLogger(__name__)


def solve_llm_constraints(
    constraints: list[Constraint],
    z3_values: dict[str, Any],
    method_info: MethodInfo,
    max_retries: int = 2,
) -> dict[str, Any]:
    """Solve constraints that Z3 cannot handle using an LLM.

    Takes the LLM-required constraints, any values already solved by Z3,
    and the method info. Returns a merged dict of parameter → value.
    """
    if not constraints:
        return dict(z3_values)

    method_signature = _format_method_signature(method_info)
    constraints_text = _format_constraints(constraints, z3_values)
    variable_types = _format_variable_types(method_info.parameters)

    prompt = CONSTRAINT_SOLVING_PROMPT.format(
        method_signature=method_signature,
        constraints=constraints_text,
        variable_types=variable_types,
    )

    for attempt in range(1, max_retries + 1):
        try:
            llm_values = call_llm_json(prompt, system=CONSTRAINT_SOLVING_SYSTEM)
            if not isinstance(llm_values, dict):
                logger.warning(
                    "LLM returned non-dict on attempt %d: %s", attempt, type(llm_values)
                )
                continue

            # Merge: Z3 values take precedence for variables they solved,
            # LLM fills in the rest
            merged = dict(z3_values)
            for key, val in llm_values.items():
                if key not in merged:
                    merged[key] = val

            return merged

        except Exception as exc:
            logger.warning("LLM solving attempt %d failed: %s", attempt, exc)

    # All retries exhausted — return Z3 values only
    logger.warning(
        "LLM solver failed after %d attempts, returning Z3 values only",
        max_retries,
    )
    return dict(z3_values)


def solve_llm_constraints_batch(
    items: list[tuple[list[Constraint], dict[str, Any], MethodInfo]],
    *,
    max_workers: int = 8,
) -> list[dict[str, Any]]:
    """Solve multiple constraint sets concurrently via the LLM.

    Each item is (constraints, z3_values, method_info).  Items with no
    LLM constraints are short-circuited without an API call.
    """
    # Separate items that need LLM calls from those that don't
    need_llm: list[tuple[int, str]] = []  # (index, prompt)
    results: list[dict[str, Any]] = [{}] * len(items)

    for idx, (constraints, z3_values, method_info) in enumerate(items):
        if not constraints:
            results[idx] = dict(z3_values)
            continue

        method_signature = _format_method_signature(method_info)
        constraints_text = _format_constraints(constraints, z3_values)
        variable_types = _format_variable_types(method_info.parameters)

        prompt = CONSTRAINT_SOLVING_PROMPT.format(
            method_signature=method_signature,
            constraints=constraints_text,
            variable_types=variable_types,
        )
        need_llm.append((idx, prompt))

    if not need_llm:
        return results

    # Batch call
    prompts = [(prompt, CONSTRAINT_SOLVING_SYSTEM) for _, prompt in need_llm]
    llm_results = call_llm_json_batch(prompts, max_workers=max_workers)

    for (idx, _), llm_values in zip(need_llm, llm_results):
        z3_values = items[idx][1]
        merged = dict(z3_values)
        if isinstance(llm_values, dict):
            for key, val in llm_values.items():
                if key not in merged:
                    merged[key] = val
        else:
            logger.warning("LLM batch returned non-dict for item %d: %s", idx, type(llm_values))
        results[idx] = merged

    return results


def _format_method_signature(method_info: MethodInfo) -> str:
    """Format a MethodInfo into a Java-like signature string."""
    params = ", ".join(
        f"{p.java_type} {p.name}" for p in method_info.parameters
    )
    ret = method_info.return_type or "void"
    return f"{ret} {method_info.name}({params})"


def _format_constraints(
    constraints: list[Constraint], z3_values: dict[str, Any]
) -> str:
    """Format constraints and pre-solved values into a readable list."""
    lines: list[str] = []

    # Show pre-solved Z3 values
    if z3_values:
        lines.append("Already solved by Z3:")
        for var, val in z3_values.items():
            lines.append(f"  {var} = {val!r}")
        lines.append("")

    lines.append("Constraints to satisfy:")
    for c in constraints:
        prefix = "NOT " if c.negated else ""
        lines.append(f"  {prefix}{c.condition.source_expr}")

    return "\n".join(lines)


def _format_variable_types(parameters: list[Parameter]) -> str:
    """Format parameter types for the prompt."""
    return "\n".join(f"  {p.name}: {p.java_type}" for p in parameters)
