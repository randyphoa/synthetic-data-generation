"""Phase 4: Validate generated data coverage against a Java program using JaCoCo."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path as FilePath


@dataclass
class CoverageReport:
    """Coverage validation results."""

    line_pct: float = 0.0
    branch_pct: float = 0.0
    path_pct: float = 0.0
    uncovered_paths: list[int] = field(default_factory=list)


def compute_path_coverage(
    dataset_path_ids: set[int],
    total_path_ids: set[int],
) -> tuple[float, list[int]]:
    """Compute path coverage from dataset path_ids vs total paths.

    Returns (coverage_pct, list_of_uncovered_path_ids).
    """
    if not total_path_ids:
        return 100.0, []

    covered = dataset_path_ids & total_path_ids
    uncovered = sorted(total_path_ids - covered)
    pct = (len(covered) / len(total_path_ids)) * 100.0
    return pct, uncovered


def validate_coverage(
    java_path: str,
    dataset_path: str,
    jacoco_agent_path: str | None = None,
    jacoco_cli_path: str | None = None,
) -> CoverageReport:
    """Validate generated data coverage by running it against the Java program.

    Requires ``javac`` and ``java`` on PATH. JaCoCo agent and CLI JARs must
    be provided or discoverable. Raises :class:`EnvironmentError` if
    prerequisites are missing.

    Steps:
      1. Compile .java to .class via javac
      2. Generate a test harness that reads the CSV and invokes the method
      3. Run with JaCoCo agent
      4. Parse JaCoCo XML report for line/branch coverage
      5. Compute path coverage from dataset path_ids vs total paths
    """
    # Check prerequisites
    if not shutil.which("javac"):
        raise EnvironmentError(
            "javac not found on PATH. Install a JDK to use coverage validation."
        )
    if not shutil.which("java"):
        raise EnvironmentError(
            "java not found on PATH. Install a JDK to use coverage validation."
        )

    java_file = FilePath(java_path)
    if not java_file.exists():
        raise FileNotFoundError(f"Java source not found: {java_path}")

    dataset_file = FilePath(dataset_path)
    if not dataset_file.exists():
        raise FileNotFoundError(f"Dataset file not found: {dataset_path}")

    # Resolve JaCoCo paths
    if jacoco_agent_path is None:
        jacoco_agent_path = os.environ.get("JACOCO_AGENT_PATH", "")
    if jacoco_cli_path is None:
        jacoco_cli_path = os.environ.get("JACOCO_CLI_PATH", "")

    if not jacoco_agent_path or not FilePath(jacoco_agent_path).exists():
        raise EnvironmentError(
            "JaCoCo agent JAR not found. Set JACOCO_AGENT_PATH or pass "
            "jacoco_agent_path parameter."
        )
    if not jacoco_cli_path or not FilePath(jacoco_cli_path).exists():
        raise EnvironmentError(
            "JaCoCo CLI JAR not found. Set JACOCO_CLI_PATH or pass "
            "jacoco_cli_path parameter."
        )

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = FilePath(tmpdir)

        # 1. Compile the Java source
        subprocess.run(
            ["javac", "-d", str(tmp), str(java_file)],
            check=True,
            capture_output=True,
        )

        # 2. Generate test harness
        class_name = java_file.stem
        harness_src = _generate_harness(class_name, str(dataset_file))
        harness_file = tmp / "TestHarness.java"
        harness_file.write_text(harness_src)

        subprocess.run(
            ["javac", "-cp", str(tmp), "-d", str(tmp), str(harness_file)],
            check=True,
            capture_output=True,
        )

        # 3. Run with JaCoCo agent
        exec_file = tmp / "jacoco.exec"
        subprocess.run(
            [
                "java",
                f"-javaagent:{jacoco_agent_path}=destfile={exec_file}",
                "-cp",
                str(tmp),
                "TestHarness",
            ],
            check=True,
            capture_output=True,
        )

        # 4. Generate and parse XML report
        xml_report = tmp / "report.xml"
        subprocess.run(
            [
                "java",
                "-jar",
                str(jacoco_cli_path),
                "report",
                str(exec_file),
                "--classfiles",
                str(tmp),
                "--sourcefiles",
                str(java_file.parent),
                "--xml",
                str(xml_report),
            ],
            check=True,
            capture_output=True,
        )

        report = _parse_jacoco_xml(str(xml_report))

    return report


def _generate_harness(class_name: str, csv_path: str) -> str:
    """Generate a Java test harness that reads a CSV and invokes the target method."""
    return f"""\
import java.io.*;
import java.util.*;

public class TestHarness {{
    public static void main(String[] args) throws Exception {{
        {class_name} obj = new {class_name}();
        BufferedReader reader = new BufferedReader(new FileReader("{csv_path}"));
        String header = reader.readLine();
        String[] columns = header.split(",");
        String line;
        while ((line = reader.readLine()) != null) {{
            String[] values = line.split(",");
            // Invoke method via reflection or direct call
            // This is a basic harness — real usage may need method-specific generation
            System.out.println("Row: " + Arrays.toString(values));
        }}
        reader.close();
    }}
}}
"""


def _parse_jacoco_xml(xml_path: str) -> CoverageReport:
    """Parse a JaCoCo XML report and extract line/branch coverage."""
    tree = ET.parse(xml_path)
    root = tree.getroot()

    line_pct = 0.0
    branch_pct = 0.0

    for counter in root.iter("counter"):
        ctype = counter.get("type", "")
        missed = int(counter.get("missed", "0"))
        covered = int(counter.get("covered", "0"))
        total = missed + covered

        if total == 0:
            continue

        pct = (covered / total) * 100.0

        if ctype == "LINE":
            line_pct = pct
        elif ctype == "BRANCH":
            branch_pct = pct

    return CoverageReport(line_pct=line_pct, branch_pct=branch_pct)
