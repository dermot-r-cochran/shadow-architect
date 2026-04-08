"""Coverage evaluator.

Measures the degree to which source files are exercised by the test suite.
When source files are provided with their content, this module counts
function / class definitions and estimates how many are referenced in tests.
"""

from __future__ import annotations

import ast
import re
from dataclasses import dataclass, field
from pathlib import Path

from shadow_architect.core.models import Finding, Severity, TestSuite


@dataclass
class CoverageResult:
    """Coverage statistics for a test suite."""

    total_symbols: int = 0
    covered_symbols: int = 0
    uncovered_symbols: list[str] = field(default_factory=list)
    findings: list[Finding] = field(default_factory=list)

    @property
    def coverage_percent(self) -> float:
        if self.total_symbols == 0:
            return 100.0
        return round(self.covered_symbols / self.total_symbols * 100, 1)


class CoverageEvaluator:
    """Estimates symbol coverage without running code instrumentation.

    A lightweight static approximation: extracts top-level function and class
    names from source files, then checks whether those names appear in any of
    the test files.  This is not a substitute for runtime coverage tools
    (e.g., ``coverage.py``) but gives a fast indicator without needing to
    install or execute the project.
    """

    def evaluate(self, suite: TestSuite) -> CoverageResult:
        result = CoverageResult()

        symbols = self._extract_symbols(suite.source_files)
        result.total_symbols = len(symbols)
        if not symbols:
            return result

        test_content = self._read_test_content(suite.test_files)

        for symbol in symbols:
            # Simple name reference check – not perfect but lightweight
            pattern = re.compile(r"\b" + re.escape(symbol) + r"\b")
            if pattern.search(test_content):
                result.covered_symbols += 1
            else:
                result.uncovered_symbols.append(symbol)

        if result.coverage_percent < 80.0:
            result.findings.append(
                Finding(
                    id="low-symbol-coverage",
                    title="Low estimated symbol coverage",
                    description=(
                        f"Only {result.coverage_percent}% of source symbols appear to be "
                        "referenced in tests. Consider adding tests for untested components."
                    ),
                    severity=Severity.MEDIUM,
                    category="coverage",
                )
            )

        return result

    # ------------------------------------------------------------------

    def _extract_symbols(self, source_files: list[str]) -> list[str]:
        symbols: list[str] = []
        for file_path in source_files:
            path = Path(file_path)
            if not path.exists() or path.suffix != ".py":
                continue
            try:
                tree = ast.parse(path.read_text(encoding="utf-8", errors="replace"))
            except SyntaxError:
                continue
            for node in ast.walk(tree):
                if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if not node.name.startswith("_"):
                        symbols.append(node.name)
                elif isinstance(node, ast.ClassDef):
                    if not node.name.startswith("_"):
                        symbols.append(node.name)
        return symbols

    def _read_test_content(self, test_files: list[str]) -> str:
        parts: list[str] = []
        for file_path in test_files:
            path = Path(file_path)
            if path.exists():
                try:
                    parts.append(path.read_text(encoding="utf-8", errors="replace"))
                except OSError:
                    pass
        return "\n".join(parts)
