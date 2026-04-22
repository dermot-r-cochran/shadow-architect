"""Anti-pattern detector for test constructs that obscure failures.

Identifies test code patterns that suppress, hide, or misrepresent failure
signals — such as bare ``except`` clauses, trivial constant assertions, and
test functions too large to have a clear containment intent.
"""

from __future__ import annotations

import ast
from dataclasses import dataclass, field
from pathlib import Path

from shadow_architect.core.models import Finding, Severity


@dataclass
class QualityResult:
    """Aggregated anti-pattern findings across all analysed test files."""

    files_evaluated: int = 0
    tests_evaluated: int = 0
    anti_patterns_found: int = 0
    quality_score: float = 100.0
    findings: list[Finding] = field(default_factory=list)


class QualityEvaluator:
    """Detects test constructs that obscure or suppress failure signals.

    Anti-patterns checked:

    * ``assert True`` / ``assert False`` (assertion provides no containment signal)
    * Bare ``except`` or ``except Exception`` (failure may be swallowed silently)
    * Test functions longer than 50 lines (containment intent is unclear)
    """

    _MAX_TEST_LINES = 50
    _PENALTY_PER_ISSUE = 5.0

    def evaluate(self, test_files: list[str]) -> QualityResult:
        result = QualityResult()
        for file_path in test_files:
            path = Path(file_path)
            if not path.exists() or path.suffix != ".py":
                continue
            try:
                source = path.read_text(encoding="utf-8", errors="replace")
                tree = ast.parse(source, filename=str(path))
            except (OSError, SyntaxError):
                continue
            result.files_evaluated += 1
            self._check_tree(tree, path, result)

        # Deduct penalties
        penalty = min(
            result.anti_patterns_found * self._PENALTY_PER_ISSUE, 100.0
        )
        result.quality_score = max(0.0, 100.0 - penalty)
        return result

    # ------------------------------------------------------------------

    def _check_tree(
        self, tree: ast.Module, path: Path, result: QualityResult
    ) -> None:
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                if not node.name.startswith("test_"):
                    continue
                result.tests_evaluated += 1
                self._check_test_function(node, path, result)

    def _check_test_function(
        self,
        func: ast.FunctionDef | ast.AsyncFunctionDef,
        path: Path,
        result: QualityResult,
    ) -> None:
        location = f"{path}::{func.name}"

        # Check function length
        start = func.lineno
        end = getattr(func, "end_lineno", start)
        if (end - start) > self._MAX_TEST_LINES:
            result.anti_patterns_found += 1
            result.findings.append(
                Finding(
                    id=f"long-test-{path.name}-{func.name}",
                    title="Test function is too long",
                    description=(
                        f"'{func.name}' spans {end - start} lines "
                        f"(max recommended: {self._MAX_TEST_LINES}). "
                        "Consider splitting into smaller, focused tests."
                    ),
                    severity=Severity.LOW,
                    category="quality",
                    location=location,
                )
            )

        for child in ast.walk(func):
            # Detect assert True / assert False
            if isinstance(child, ast.Assert):
                val = child.test
                if isinstance(val, ast.Constant) and val.value in (True, False):
                    result.anti_patterns_found += 1
                    result.findings.append(
                        Finding(
                            id=f"trivial-assert-{path.name}-{func.name}",
                            title="Trivial assertion (assert True/False)",
                            description=(
                                f"'{func.name}' contains 'assert {val.value}' which "
                                "is always True/False and provides no real verification."
                            ),
                            severity=Severity.MEDIUM,
                            category="quality",
                            location=location,
                        )
                    )

            # Detect bare except / except Exception
            if isinstance(child, ast.ExceptHandler):
                if child.type is None:
                    result.anti_patterns_found += 1
                    result.findings.append(
                        Finding(
                            id=f"bare-except-{path.name}-{func.name}",
                            title="Bare except clause in test",
                            description=(
                                f"'{func.name}' contains a bare 'except:' clause which "
                                "may silently swallow failures."
                            ),
                            severity=Severity.MEDIUM,
                            category="quality",
                            location=location,
                        )
                    )
                elif (
                    isinstance(child.type, ast.Name)
                    and child.type.id == "Exception"
                ):
                    result.anti_patterns_found += 1
                    result.findings.append(
                        Finding(
                            id=f"broad-except-{path.name}-{func.name}",
                            title="Overly broad except Exception in test",
                            description=(
                                f"'{func.name}' catches 'Exception' broadly, which may "
                                "hide unexpected failures."
                            ),
                            severity=Severity.LOW,
                            category="quality",
                            location=location,
                        )
                    )
