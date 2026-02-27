"""Phase 2b: LLM-powered SQL condition extraction from DAO classes."""

from __future__ import annotations

import logging

from synthetic_data.llm.client import call_llm_json
from synthetic_data.llm.prompts import SQL_EXTRACTION_PROMPT, SQL_EXTRACTION_SYSTEM
from synthetic_data.models.sql import DAOMethodSQL, SQLCondition

logger = logging.getLogger(__name__)


def extract_sql_conditions(dao_path: str) -> list[DAOMethodSQL]:
    """Extract SQL conditions from a DAO Java class using an LLM.

    Reads the DAO source file, sends it to the LLM for structured
    extraction, validates the result with sqlglot, and returns typed models.
    """
    with open(dao_path, "r", encoding="utf-8") as f:
        dao_source = f.read()

    return extract_sql_conditions_from_source(dao_source)


def extract_sql_conditions_from_source(dao_source: str) -> list[DAOMethodSQL]:
    """Extract SQL conditions from DAO source code string."""
    prompt = SQL_EXTRACTION_PROMPT.format(dao_source=dao_source)
    raw = call_llm_json(prompt, system=SQL_EXTRACTION_SYSTEM)

    if isinstance(raw, dict):
        # LLM may wrap in a top-level key
        for key in ("methods", "results", "queries", "data"):
            if key in raw and isinstance(raw[key], list):
                raw = raw[key]
                break
        else:
            raw = [raw]

    results: list[DAOMethodSQL] = []
    for entry in raw:
        try:
            dao_method = _parse_entry(entry)
            results.append(dao_method)
        except (KeyError, TypeError) as exc:
            logger.warning("Skipping malformed LLM entry: %s — %s", entry, exc)

    return results


def validate_sql(sql: str) -> bool:
    """Validate a SQL string using sqlglot.

    Returns True if the SQL parses successfully, False otherwise.
    """
    try:
        import sqlglot

        parsed = sqlglot.parse(sql)
        return len(parsed) > 0 and parsed[0] is not None
    except Exception:
        return False


def _parse_entry(entry: dict) -> DAOMethodSQL:
    """Parse a single LLM-returned dict into a DAOMethodSQL model."""
    conditions = [
        SQLCondition(
            column=c["column"],
            operator=c["operator"],
            value=c.get("value", "?"),
            dto_field=c.get("dto_field", ""),
        )
        for c in entry.get("conditions", [])
    ]

    joins = entry.get("joins", []) or []
    hardcoded = entry.get("hardcoded_values", []) or []

    return DAOMethodSQL(
        method=entry["method"],
        table=entry.get("table", ""),
        conditions=conditions,
        joins=joins,
        hardcoded_values=hardcoded,
    )
