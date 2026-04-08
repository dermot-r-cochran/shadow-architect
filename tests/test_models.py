"""Tests for shadow_architect.core.models."""

import pytest
from shadow_architect.core.models import (
    Finding,
    Recommendation,
    Severity,
    TestSuite,
    TestType,
)


def test_finding_str_with_location():
    f = Finding(
        id="f1",
        title="Test finding",
        description="A description",
        severity=Severity.HIGH,
        category="quality",
        location="tests/test_foo.py::test_bar",
    )
    result = str(f)
    assert "[HIGH]" in result
    assert "Test finding" in result
    assert "tests/test_foo.py" in result


def test_finding_str_without_location():
    f = Finding(
        id="f2",
        title="No location",
        description="desc",
        severity=Severity.LOW,
        category="coverage",
    )
    result = str(f)
    assert "[LOW]" in result
    assert "[" not in result.split("]", 1)[-1].split(":")[0]


def test_recommendation_str():
    rec = Recommendation(
        id="r1",
        title="Add tests",
        description="Please add tests.",
        priority=Severity.CRITICAL,
        category="coverage",
    )
    result = str(rec)
    assert "[CRITICAL]" in result
    assert "Add tests" in result


def test_test_suite_defaults():
    suite = TestSuite(name="Demo Suite")
    assert suite.test_files == []
    assert suite.test_types == []
    assert suite.source_files == []
    assert suite.metadata == {}


@pytest.mark.parametrize(
    "severity,expected",
    [
        (Severity.CRITICAL, "critical"),
        (Severity.HIGH, "high"),
        (Severity.MEDIUM, "medium"),
        (Severity.LOW, "low"),
        (Severity.INFO, "info"),
    ],
)
def test_severity_values(severity, expected):
    assert severity.value == expected


@pytest.mark.parametrize(
    "test_type,expected",
    [
        (TestType.UNIT, "unit"),
        (TestType.ADVERSARIAL, "adversarial"),
        (TestType.SECURITY, "security"),
    ],
)
def test_test_type_values(test_type, expected):
    assert test_type.value == expected
