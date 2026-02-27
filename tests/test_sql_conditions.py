"""Tests for Phase 2b: SQL condition extraction from DAO classes."""

from pathlib import Path
from unittest.mock import patch

import pytest

from synthetic_data.extraction.sql_conditions import (
    extract_sql_conditions,
    extract_sql_conditions_from_source,
    validate_sql,
    _parse_entry,
)
from synthetic_data.models.sql import DAOMethodSQL, SQLCondition

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# --- Realistic LLM response for SampleDAO.java ---

SAMPLE_LLM_RESPONSE = [
    {
        "method": "findActiveCustomersByCreditRange",
        "table": "T_CUSTOMER",
        "conditions": [
            {"column": "CUST_STS_CDE", "operator": "=", "value": "A", "dto_field": "custStsCde"},
            {"column": "CUST_CRDT_SCR", "operator": ">=", "value": "?", "dto_field": "custCrdtScr"},
            {"column": "CUST_CRDT_SCR", "operator": "<", "value": "?", "dto_field": "custCrdtScr"},
        ],
        "joins": [],
        "hardcoded_values": [{"column": "CUST_STS_CDE", "value": "A"}],
    },
    {
        "method": "findByStatusAndEmploymentType",
        "table": "T_CUSTOMER",
        "conditions": [
            {"column": "CUST_STS_CDE", "operator": "=", "value": "?", "dto_field": "custStsCde"},
            {"column": "CUST_EMPL_TP_CDE", "operator": "=", "value": "?", "dto_field": "custEmplTpCde"},
        ],
        "joins": [],
        "hardcoded_values": [],
    },
    {
        "method": "countCustomersByMemberDate",
        "table": "T_CUSTOMER",
        "conditions": [
            {"column": "CUST_MBR_SINCE_DT", "operator": "<=", "value": "?", "dto_field": "custMbrSinceDt"},
            {"column": "CUST_STS_CDE", "operator": "=", "value": "?", "dto_field": "custStsCde"},
        ],
        "joins": [],
        "hardcoded_values": [],
    },
    {
        "method": "findClosedCustomers",
        "table": "T_CUSTOMER",
        "conditions": [
            {"column": "CUST_STS_CDE", "operator": "=", "value": "C", "dto_field": "custStsCde"},
            {"column": "CUST_MBR_SINCE_DT", "operator": "<", "value": "?", "dto_field": "custMbrSinceDt"},
        ],
        "joins": [],
        "hardcoded_values": [{"column": "CUST_STS_CDE", "value": "C"}],
    },
]


class TestParseEntry:
    """Test _parse_entry converting raw dicts to DAOMethodSQL models."""

    def test_basic_entry(self):
        entry = {
            "method": "findAll",
            "table": "USERS",
            "conditions": [
                {"column": "STATUS", "operator": "=", "value": "?", "dto_field": "status"},
            ],
            "joins": [],
            "hardcoded_values": [],
        }
        result = _parse_entry(entry)
        assert isinstance(result, DAOMethodSQL)
        assert result.method == "findAll"
        assert result.table == "USERS"
        assert len(result.conditions) == 1
        assert result.conditions[0].column == "STATUS"
        assert result.conditions[0].operator == "="

    def test_missing_optional_fields(self):
        entry = {"method": "findById", "conditions": []}
        result = _parse_entry(entry)
        assert result.method == "findById"
        assert result.table == ""
        assert result.conditions == []
        assert result.joins == []
        assert result.hardcoded_values == []

    def test_missing_method_raises(self):
        with pytest.raises(KeyError):
            _parse_entry({"table": "T"})

    def test_condition_default_value(self):
        entry = {
            "method": "find",
            "conditions": [{"column": "COL", "operator": "="}],
        }
        result = _parse_entry(entry)
        assert result.conditions[0].value == "?"
        assert result.conditions[0].dto_field == ""


class TestExtractSqlConditionsFromSource:
    """Test the full extraction pipeline with mocked LLM."""

    @patch("synthetic_data.extraction.sql_conditions.call_llm_json")
    def test_extracts_all_methods(self, mock_llm):
        mock_llm.return_value = SAMPLE_LLM_RESPONSE
        dao_source = (FIXTURES_DIR / "SampleDAO.java").read_text()

        results = extract_sql_conditions_from_source(dao_source)

        assert len(results) == 4
        assert all(isinstance(r, DAOMethodSQL) for r in results)
        methods = [r.method for r in results]
        assert "findActiveCustomersByCreditRange" in methods
        assert "findByStatusAndEmploymentType" in methods
        assert "countCustomersByMemberDate" in methods
        assert "findClosedCustomers" in methods

    @patch("synthetic_data.extraction.sql_conditions.call_llm_json")
    def test_conditions_parsed_correctly(self, mock_llm):
        mock_llm.return_value = SAMPLE_LLM_RESPONSE
        dao_source = (FIXTURES_DIR / "SampleDAO.java").read_text()

        results = extract_sql_conditions_from_source(dao_source)
        active_method = next(
            r for r in results if r.method == "findActiveCustomersByCreditRange"
        )

        assert len(active_method.conditions) == 3
        assert active_method.conditions[0].column == "CUST_STS_CDE"
        assert active_method.conditions[0].value == "A"
        assert active_method.conditions[1].operator == ">="
        assert active_method.conditions[2].operator == "<"

    @patch("synthetic_data.extraction.sql_conditions.call_llm_json")
    def test_hardcoded_values(self, mock_llm):
        mock_llm.return_value = SAMPLE_LLM_RESPONSE
        dao_source = (FIXTURES_DIR / "SampleDAO.java").read_text()

        results = extract_sql_conditions_from_source(dao_source)
        closed = next(r for r in results if r.method == "findClosedCustomers")

        assert len(closed.hardcoded_values) == 1
        assert closed.hardcoded_values[0]["column"] == "CUST_STS_CDE"
        assert closed.hardcoded_values[0]["value"] == "C"

    @patch("synthetic_data.extraction.sql_conditions.call_llm_json")
    def test_handles_wrapped_response(self, mock_llm):
        """LLM might wrap results in a top-level key."""
        mock_llm.return_value = {"methods": SAMPLE_LLM_RESPONSE}

        results = extract_sql_conditions_from_source("class Foo {}")
        assert len(results) == 4

    @patch("synthetic_data.extraction.sql_conditions.call_llm_json")
    def test_handles_single_dict_response(self, mock_llm):
        """LLM might return a single object instead of an array."""
        mock_llm.return_value = {
            "method": "findById",
            "table": "USERS",
            "conditions": [{"column": "ID", "operator": "=", "value": "?", "dto_field": "id"}],
            "joins": [],
            "hardcoded_values": [],
        }
        results = extract_sql_conditions_from_source("class Foo {}")
        assert len(results) == 1
        assert results[0].method == "findById"

    @patch("synthetic_data.extraction.sql_conditions.call_llm_json")
    def test_skips_malformed_entries(self, mock_llm):
        mock_llm.return_value = [
            {"method": "good", "conditions": []},
            {"bad": "entry"},  # missing "method"
        ]
        results = extract_sql_conditions_from_source("class Foo {}")
        assert len(results) == 1
        assert results[0].method == "good"


class TestExtractSqlConditionsFromFile:
    """Test file-based extraction."""

    @patch("synthetic_data.extraction.sql_conditions.call_llm_json")
    def test_reads_file_and_extracts(self, mock_llm):
        mock_llm.return_value = SAMPLE_LLM_RESPONSE
        dao_path = str(FIXTURES_DIR / "SampleDAO.java")

        results = extract_sql_conditions(dao_path)

        assert len(results) == 4
        # Verify the prompt received the file contents
        call_args = mock_llm.call_args
        assert "SampleDAO" in call_args[0][0]


class TestValidateSql:
    """Test SQL validation via sqlglot."""

    def test_valid_select(self):
        assert validate_sql("SELECT * FROM users WHERE id = 1") is True

    def test_valid_complex(self):
        sql = (
            "SELECT * FROM T_CUSTOMER "
            "WHERE CUST_STS_CDE = 'A' "
            "AND CUST_CRDT_SCR >= 700 "
            "AND CUST_CRDT_SCR < 800"
        )
        assert validate_sql(sql) is True

    def test_invalid_sql(self):
        assert validate_sql("NOT VALID SQL !!!! FROM") is False

    def test_empty_string(self):
        assert validate_sql("") is False
