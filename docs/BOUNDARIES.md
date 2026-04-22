# shadow-architect: System Boundaries

This document is a concrete reference for the boundaries enforced by shadow-architect. Each boundary maps to a specific check, gate, or containment experiment in the tool.

---

## Red Lines — Unacceptable States

These states must never occur. A validation run that leaves any of these unchecked is incomplete.

| Unacceptable State | How This Boundary Is Enforced |
|---|---|
| Prompt injection achieves instruction override | `AdversarialEvaluator`: checks for `PROMPT_INJECTION` category coverage in the test suite. If absent, a HIGH finding is raised. Gate: AI products cannot release without this category covered. |
| Sensitive data (PII, credentials, system prompt) disclosed via model output | `AdversarialEvaluator`: checks for `SENSITIVE_INFO_DISCLOSURE` and `DATA_EXFILTRATION` categories. Both are CRITICAL severity if uncovered. |
| Unsafe output (executable code, injection payload) reaches a downstream consumer | `AdversarialEvaluator`: checks for `INSECURE_OUTPUT` category. CRITICAL severity if uncovered. |
| Agentic system takes irreversible external action without a human decision gate | `SecurityChaosExperiment`: verifies that credential-absent and permission-denied conditions do not silently succeed. The decision gate itself must be enforced in application code; this experiment confirms it is not bypassed silently. |
| System fails without surfacing the failure under adversarial input | `CorruptInputExperiment`: verifies that malformed, null, and boundary-value inputs do not produce unhandled exceptions that are silently swallowed. |

---

## Tolerable-but-Visible Risk States

These states are permitted under defined conditions but must appear as findings in the validation output. They do not pass silently.

| Risk State | Condition for Tolerance | How It Is Surfaced |
|---|---|---|
| Integration tests absent | Early-stage development, declared as a known gap | `IntegrationTestPresenceCriterion`: MEDIUM finding if integration tests are not detected |
| Adversarial category partially covered | Deferred categories are explicitly named, not silently absent | `AdversarialEvaluator`: lists `categories_missing` in the result; HIGH finding raised |
| Hallucination or factual error in non-binding output | System does not present output as verified; no downstream decision depends on the output | `AdversarialEvaluator`: checks `HALLUCINATION` category; HIGH finding if uncovered |
| Missing test isolation (mocks absent) | Suite has ≤5 tests | `TestIsolationCriterion` and `QualityEvaluator`: LOW finding surfaced for larger suites |
| Source symbols without corresponding test references | Components not declared as boundary-critical | `CoverageEvaluator`: MEDIUM finding if symbol coverage falls below 80% |
| Tests with broad exception handling | Explicitly acknowledged as a known structural issue | `QualityEvaluator`: finding raised for each `except Exception` or bare `except` detected |

---

## Acceptable Variability

These vary without triggering findings or requiring escalation:

| Variable | Why It Is Acceptable |
|---|---|
| Assertion density differences across test types | Integration and end-to-end tests may legitimately have lower assertion density than unit tests |
| Test file naming conventions | Naming does not affect boundary enforcement |
| Choice of mocking library (unittest.mock, pytest-mock, etc.) | The tool detects mock presence by pattern; library choice does not affect detection |
| Fixture implementation style | Fixtures are counted but not validated for correctness |
| Coverage percentage in non-boundary-critical source files | Only components whose failure has boundary-level impact require coverage tracking |
| Parameter count in parametrized tests | The tool detects parametrization presence; parameter count is not enforced |

---

## Boundary-to-Check Mapping

This table maps each boundary to the specific validator criterion, evaluator, or chaos experiment that enforces it.

| Boundary | Component | Criterion / Experiment ID |
|---|---|---|
| Test suite contains at least one check | `TestValidator` | `has-tests` |
| Tests make observable assertions (density ≥ 1.0) | `TestValidator` | `assertion-density` |
| Unit-level boundary checks present | `TestValidator` | `unit-tests-present` |
| Integration boundary checks present | `TestValidator` | `integration-tests-present` |
| AI/LLM failure class coverage present | `TestValidator` + `AdversarialEvaluator` | `adversarial-tests-present` |
| Security boundary checks present for API/cloud products | `TestValidator` | `security-tests-present` |
| Tests do not have uncontrolled external dependencies | `TestValidator` | `test-isolation` |
| Prompt injection boundary covered | `AdversarialEvaluator` | `PROMPT_INJECTION` category |
| Data exfiltration boundary covered | `AdversarialEvaluator` | `DATA_EXFILTRATION` category |
| Insecure output boundary covered | `AdversarialEvaluator` | `INSECURE_OUTPUT` category |
| Sensitive info disclosure boundary covered | `AdversarialEvaluator` | `SENSITIVE_INFO_DISCLOSURE` category |
| Jailbreak boundary covered | `AdversarialEvaluator` | `JAILBREAK` category |
| Hallucination boundary covered | `AdversarialEvaluator` | `HALLUCINATION` category |
| DoS / resource exhaustion boundary covered | `AdversarialEvaluator` | `DENIAL_OF_SERVICE` category |
| Bias boundary covered | `AdversarialEvaluator` | `BIAS` category |
| Corrupt input containment | `CorruptInputExperiment` | chaos: `corrupt-inputs` |
| Credential-absent containment | `SecurityChaosExperiment` | chaos: `security` |
| Network disruption containment | `NetworkChaosExperiment` | chaos: `network` |
| Uncovered source symbols (boundary gap detection) | `CoverageEvaluator` | `low-symbol-coverage` |
| Vacuous assertions (constraint enforcement absent) | `QualityEvaluator` | `trivial-assert-*` |
| Silent failure swallowing | `QualityEvaluator` | `bare-except-*`, `broad-except-*` |
