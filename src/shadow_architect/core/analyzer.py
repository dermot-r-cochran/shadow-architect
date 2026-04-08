"""Test strategy analyzer module.

Analyzes an existing test strategy and test suite to identify its structure,
coverage, and gaps relative to the declared use case or product requirements.
"""

from __future__ import annotations

import ast
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from shadow_architect.core.models import Finding, Severity, TestSuite, TestType


@dataclass
class StrategyAnalysis:
    """Results produced by the TestStrategyAnalyzer."""

    suite: TestSuite
    test_count: int = 0
    test_types_found: list[TestType] = field(default_factory=list)
    test_files_analyzed: list[str] = field(default_factory=list)
    assertion_count: int = 0
    mock_count: int = 0
    fixture_count: int = 0
    parametrized_count: int = 0
    missing_test_types: list[TestType] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def assertion_density(self) -> float:
        """Average assertions per test (a quality indicator)."""
        if self.test_count == 0:
            return 0.0
        return self.assertion_count / self.test_count

    @property
    def has_adequate_coverage(self) -> bool:
        """True when no CRITICAL or HIGH findings exist."""
        return not any(
            f.severity in (Severity.CRITICAL, Severity.HIGH) for f in self.findings
        )


class TestStrategyAnalyzer:
    """Analyzes existing test suites to discover gaps and structural issues.

    Supports Python test files (pytest / unittest style).  Non-Python test
    artefacts are captured as metadata rather than deep-parsed.
    """

    # Patterns used during AST-free scanning
    _TEST_FUNC_RE = re.compile(r"^\s*def (test_\w+)", re.MULTILINE)
    _TEST_CLASS_RE = re.compile(r"^\s*class (Test\w+)", re.MULTILINE)
    _ASSERT_RE = re.compile(r"\bassert\b", re.MULTILINE)
    _MOCK_RE = re.compile(r"\b(Mock|MagicMock|patch|mocker)\b", re.MULTILINE)
    _FIXTURE_RE = re.compile(r"@pytest\.fixture", re.MULTILINE)
    _PARAMETRIZE_RE = re.compile(r"@pytest\.mark\.parametrize", re.MULTILINE)

    # Keywords that hint at a particular test type in file names / content
    _TYPE_HINTS: dict[TestType, list[str]] = {
        TestType.UNIT: ["unit"],
        TestType.INTEGRATION: ["integration", "e2e", "end_to_end", "end-to-end"],
        TestType.PERFORMANCE: ["perf", "performance", "load", "stress", "benchmark"],
        TestType.SECURITY: ["security", "auth", "authz", "injection", "pentest"],
        TestType.ADVERSARIAL: ["adversar", "fuzz", "robustness", "attack"],
        TestType.SMOKE: ["smoke", "sanity"],
        TestType.REGRESSION: ["regression"],
    }

    def analyze(self, suite: TestSuite) -> StrategyAnalysis:
        """Run a full analysis of *suite* and return a :class:`StrategyAnalysis`."""
        analysis = StrategyAnalysis(suite=suite)

        for test_file in suite.test_files:
            self._analyze_file(test_file, analysis)

        self._detect_test_types(analysis)
        self._detect_missing_types(suite, analysis)
        self._generate_findings(analysis)

        return analysis

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _analyze_file(self, file_path: str, analysis: StrategyAnalysis) -> None:
        """Parse a single test file and accumulate counts."""
        path = Path(file_path)
        if not path.exists():
            analysis.findings.append(
                Finding(
                    id=f"missing-file-{path.name}",
                    title="Test file not found",
                    description=f"Declared test file '{file_path}' does not exist on disk.",
                    severity=Severity.HIGH,
                    category="file_access",
                    location=file_path,
                )
            )
            return

        analysis.test_files_analyzed.append(file_path)

        if path.suffix == ".py":
            self._analyze_python_file(path, analysis)
        else:
            # Non-Python file: count by scanning for common patterns
            try:
                content = path.read_text(encoding="utf-8", errors="replace")
                analysis.test_count += len(self._TEST_FUNC_RE.findall(content))
                analysis.assertion_count += len(self._ASSERT_RE.findall(content))
            except OSError:
                pass

    def _analyze_python_file(self, path: Path, analysis: StrategyAnalysis) -> None:
        """Deep-parse a Python test file using the AST where possible."""
        source = path.read_text(encoding="utf-8", errors="replace")

        # Fallback regex counts (used when AST parsing fails)
        analysis.mock_count += len(self._MOCK_RE.findall(source))
        analysis.fixture_count += len(self._FIXTURE_RE.findall(source))
        analysis.parametrized_count += len(self._PARAMETRIZE_RE.findall(source))

        try:
            tree = ast.parse(source, filename=str(path))
        except SyntaxError as exc:
            analysis.findings.append(
                Finding(
                    id=f"syntax-error-{path.name}",
                    title="Syntax error in test file",
                    description=str(exc),
                    severity=Severity.HIGH,
                    category="syntax",
                    location=str(path),
                )
            )
            # Fallback to regex
            analysis.test_count += len(self._TEST_FUNC_RE.findall(source))
            analysis.assertion_count += len(self._ASSERT_RE.findall(source))
            return

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if node.name.startswith("test_"):
                    analysis.test_count += 1
                    # Count assert statements within this function
                    for child in ast.walk(node):
                        if isinstance(child, ast.Assert):
                            analysis.assertion_count += 1
            elif isinstance(node, ast.ClassDef) and node.name.startswith("Test"):
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        if item.name.startswith("test_"):
                            analysis.test_count += 1
                            for child in ast.walk(item):
                                if isinstance(child, ast.Assert):
                                    analysis.assertion_count += 1

    def _detect_test_types(self, analysis: StrategyAnalysis) -> None:
        """Infer which test types are present from file names and content."""
        # Use only the base file name to avoid false positives from parent
        # directory components (e.g. pytest's tmp_path test-name subdirectory).
        all_paths = " ".join(
            Path(p).name for p in analysis.test_files_analyzed
        ).lower()
        detected: list[TestType] = []
        for test_type, keywords in self._TYPE_HINTS.items():
            if any(kw in all_paths for kw in keywords):
                detected.append(test_type)

        # If no specific type can be inferred, assume unit tests exist when
        # there are test functions
        if not detected and analysis.test_count > 0:
            detected.append(TestType.UNIT)

        analysis.test_types_found = list(set(detected))
        analysis.suite.test_types = list(
            set(analysis.suite.test_types + detected)
        )

    def _detect_missing_types(self, suite: TestSuite, analysis: StrategyAnalysis) -> None:
        """Determine which recommended test types are absent."""
        # For an AI capability product we strongly recommend adversarial tests
        recommended = {TestType.UNIT, TestType.INTEGRATION}
        product_lower = (suite.product + " " + suite.use_case).lower()
        if any(kw in product_lower for kw in ("ai", "ml", "model", "llm", "gpt")):
            recommended.add(TestType.ADVERSARIAL)
            recommended.add(TestType.SECURITY)
        if any(kw in product_lower for kw in ("api", "service", "endpoint")):
            recommended.add(TestType.INTEGRATION)
        if any(kw in product_lower for kw in ("perf", "load", "throughput")):
            recommended.add(TestType.PERFORMANCE)

        analysis.missing_test_types = [
            t for t in recommended if t not in analysis.test_types_found
        ]

    def _generate_findings(self, analysis: StrategyAnalysis) -> None:
        """Append structural findings to the analysis."""
        if analysis.test_count == 0:
            analysis.findings.append(
                Finding(
                    id="no-tests",
                    title="No tests found",
                    description="No test functions were discovered in the provided test files.",
                    severity=Severity.CRITICAL,
                    category="coverage",
                )
            )
        elif analysis.assertion_density < 1.0:
            analysis.findings.append(
                Finding(
                    id="low-assertion-density",
                    title="Low assertion density",
                    description=(
                        f"Average of {analysis.assertion_density:.2f} assertions per test "
                        "(recommended ≥ 1.0). Tests without assertions may pass vacuously."
                    ),
                    severity=Severity.MEDIUM,
                    category="quality",
                )
            )

        for missing in analysis.missing_test_types:
            analysis.findings.append(
                Finding(
                    id=f"missing-{missing.value}",
                    title=f"Missing {missing.value.replace('_', ' ')} tests",
                    description=(
                        f"No {missing.value.replace('_', ' ')} tests were detected. "
                        "This test type is recommended for the declared use case / product."
                    ),
                    severity=Severity.HIGH if missing == TestType.ADVERSARIAL else Severity.MEDIUM,
                    category="coverage",
                )
            )

        if analysis.mock_count == 0 and analysis.test_count > 5:
            analysis.findings.append(
                Finding(
                    id="no-mocks",
                    title="No test doubles detected",
                    description=(
                        "No mock objects were found. Tests may have uncontrolled external "
                        "dependencies that reduce reliability and speed."
                    ),
                    severity=Severity.LOW,
                    category="isolation",
                )
            )

        os_env_vars = [k for k in os.environ if k.startswith("SECRET") or "TOKEN" in k]
        if os_env_vars:
            analysis.findings.append(
                Finding(
                    id="env-secrets",
                    title="Potential secrets in environment",
                    description=(
                        "Environment variables that may contain secrets are set. "
                        "Ensure tests do not inadvertently log or expose them."
                    ),
                    severity=Severity.INFO,
                    category="security",
                )
            )
