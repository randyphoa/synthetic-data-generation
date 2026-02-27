"""Tests for Phase 4: Coverage validation."""

import pytest

from synthetic_data.generation.coverage import (
    CoverageReport,
    compute_path_coverage,
    validate_coverage,
)


# --- CoverageReport model ---


class TestCoverageReport:
    def test_default_values(self):
        report = CoverageReport()
        assert report.line_pct == 0.0
        assert report.branch_pct == 0.0
        assert report.path_pct == 0.0
        assert report.uncovered_paths == []

    def test_custom_values(self):
        report = CoverageReport(
            line_pct=85.0,
            branch_pct=75.0,
            path_pct=100.0,
            uncovered_paths=[3, 7],
        )
        assert report.line_pct == 85.0
        assert report.branch_pct == 75.0
        assert report.path_pct == 100.0
        assert report.uncovered_paths == [3, 7]


# --- Path coverage computation ---


class TestPathCoverage:
    def test_full_coverage(self):
        dataset_ids = {1, 2, 3}
        total_ids = {1, 2, 3}
        pct, uncovered = compute_path_coverage(dataset_ids, total_ids)
        assert pct == 100.0
        assert uncovered == []

    def test_partial_coverage(self):
        dataset_ids = {1, 3}
        total_ids = {1, 2, 3, 4}
        pct, uncovered = compute_path_coverage(dataset_ids, total_ids)
        assert pct == 50.0
        assert uncovered == [2, 4]

    def test_no_coverage(self):
        dataset_ids = set()
        total_ids = {1, 2, 3}
        pct, uncovered = compute_path_coverage(dataset_ids, total_ids)
        assert pct == 0.0
        assert uncovered == [1, 2, 3]

    def test_empty_total_paths(self):
        dataset_ids = {1, 2}
        total_ids: set[int] = set()
        pct, uncovered = compute_path_coverage(dataset_ids, total_ids)
        assert pct == 100.0
        assert uncovered == []

    def test_extra_dataset_ids_ignored(self):
        dataset_ids = {1, 2, 3, 99}
        total_ids = {1, 2, 3}
        pct, uncovered = compute_path_coverage(dataset_ids, total_ids)
        assert pct == 100.0
        assert uncovered == []

    def test_uncovered_sorted(self):
        dataset_ids = {5}
        total_ids = {1, 3, 5, 2, 4}
        pct, uncovered = compute_path_coverage(dataset_ids, total_ids)
        assert uncovered == [1, 2, 3, 4]

    def test_single_path(self):
        dataset_ids = {1}
        total_ids = {1}
        pct, uncovered = compute_path_coverage(dataset_ids, total_ids)
        assert pct == 100.0
        assert uncovered == []


# --- validate_coverage prerequisites ---


class TestValidateCoveragePrereqs:
    def test_missing_java_file(self, tmp_path):
        """Should raise FileNotFoundError for missing Java source."""
        with pytest.raises((FileNotFoundError, EnvironmentError)):
            validate_coverage(
                str(tmp_path / "Missing.java"),
                str(tmp_path / "data.csv"),
            )
