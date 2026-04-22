# shadow-architect: System Boundaries Reference

This document enumerates the concrete boundary conditions that shadow-architect enforces. For each boundary, it describes the state being constrained, how it is classified, and which check or gate in the tool enforces it.

See [`docs/STRATEGY.md`](STRATEGY.md) for the full strategy context.

---

## Red Lines — Unacceptable System States

These states must never occur at release. The gate does not open while any red-line violation is present.

### R1 — No Tests Present

**State**: The declared test suite contains zero test functions.

**Why this is a red line**: A system with no tests provides no containment evidence. Any release gate that passes in this state is meaningless. The absence of tests is not a tolerable gap — it means no boundary has been checked at all.

**Enforced by**: `HasTestsCriterion` in `core/validator.py`. Finding ID: `has-tests`. Severity: CRITICAL.

---

### R2 — No Adversarial Coverage for AI/LLM Products

**State**: The product context indicates an AI or LLM capability (keywords: `ai`, `ml`, `model`, `llm`, `gpt`), and no adversarial or robustness tests are present in the suite.

**Why this is a red line**: LLM-based systems are subject to failure classes — prompt injection, jailbreak, data exfiltration — that do not appear in standard functional tests. A suite with no adversarial coverage provides no evidence that these failure classes are contained. The gap is not recoverable by adding more unit tests.

**Enforced by**: `AdversarialTestPresenceCriterion` in `core/validator.py`. Finding ID: `adversarial-tests-present`. Severity: HIGH.

Also enforced by: `AdversarialEvaluator` in `evaluators/adversarial.py`, which checks each OWASP LLM Top-10 failure class individually. Finding ID: `adversarial-gaps`. Severity: HIGH.

---

### R3 — No Security Tests for External-Facing Products

**State**: The product context indicates API, authentication, cloud, or AI/ML exposure (keywords: `api`, `endpoint`, `auth`, `cloud`, `azure`, `ai`, `ml`), and no security tests are present.

**Why this is a red line**: External-facing components that process user input, manage credentials, or interact with cloud services must have evidence that authentication, authorisation, and input-handling boundaries are enforced. Absence means no external-exposure boundary has been checked.

**Enforced by**: `SecurityTestPresenceCriterion` in `core/validator.py`. Finding ID: `security-tests-present`. Severity: HIGH.

---

### R4 — Syntax Errors in Test Files

**State**: A declared test file cannot be parsed due to a syntax error.

**Why this is a red line**: Tests that cannot be parsed cannot be executed. A suite that claims coverage but contains unparseable files is providing false assurance.

**Enforced by**: `TestStrategyAnalyzer._analyze_python_file` in `core/analyzer.py`. Finding ID: `syntax-error-{filename}`. Severity: HIGH.

---

## Tolerable but Visible Risk States

These states are permitted at release but must appear as MEDIUM or HIGH findings in every report. They may not be silently ignored or suppressed.

### T1 — Missing Integration Tests

**State**: No integration test files are detected (no file names containing `integration`, `e2e`, `end_to_end`).

**Risk**: Component boundaries have not been checked. Failures at composition points — between services, between an agent and its tools, between the system and Azure APIs — will not be detected by unit tests alone.

**Tolerable because**: Integration tests require live or mocked infrastructure and may not be available at every stage. The risk is accepted provided it is visible.

**Enforced by**: `IntegrationTestPresenceCriterion` in `core/validator.py`. Finding ID: `integration-tests-present`. Severity: MEDIUM.

---

### T2 — Missing Test Isolation

**State**: A suite with more than 5 tests contains no mocking patterns (no `Mock`, `MagicMock`, `patch`, or `mocker` usage).

**Risk**: Tests may be calling real external services. This makes results environment-dependent, non-deterministic, and potentially destructive (e.g., writing to live storage).

**Tolerable because**: Some integration tests are intentionally unmocked. The finding signals the absence of isolation evidence, not necessarily a defect.

**Enforced by**: `TestIsolationCriterion` in `core/validator.py`. Finding ID: `test-isolation`. Severity: LOW.

Also detected by: `TestStrategyAnalyzer` in `core/analyzer.py`. Finding ID: `no-mocks`. Severity: LOW.

---

### T3 — Low Symbol Coverage

**State**: Fewer than 80% of declared source symbols (top-level functions and classes) are referenced in the test files.

**Risk**: Components that are never referenced in tests have no containment evidence. They may fail silently in ways that are not detected until production.

**Tolerable because**: Not all symbols require direct test coverage; some are internal helpers or infrastructure. The 80% threshold flags gross gaps, not stylistic choices.

**Enforced by**: `CoverageEvaluator` in `evaluators/coverage.py`. Finding ID: `low-symbol-coverage`. Severity: MEDIUM.

---

### T4 — Missing Parametrised Tests

**State**: A suite with more than 3 tests contains no `pytest.mark.parametrize` usage.

**Risk**: Boundary values and equivalence classes may not be tested. Single-input tests often pass on the happy path while failing on edge inputs that the system will encounter in production.

**Tolerable because**: Not all boundary conditions require parametrisation; the finding is a signal to review whether critical boundaries are being tested.

**Enforced by**: `ParametrizedTestsCriterion` in `core/validator.py`. Finding ID: `parametrized-tests`. Severity: LOW.

---

### T5 — Potential Secrets in Environment

**State**: Environment variables matching secret-like patterns (`SECRET*`, `*TOKEN*`) are present at analysis time.

**Risk**: Tests may inadvertently log or expose secrets. The analysis environment may be contaminated.

**Tolerable because**: CI environments legitimately contain secrets for integration testing. The finding ensures the condition is visible, not that it is necessarily a defect.

**Enforced by**: `TestStrategyAnalyzer._generate_findings` in `core/analyzer.py`. Finding ID: `env-secrets`. Severity: INFO.

---

### T6 — Anti-Patterns That Hide Failures

**State**: Test functions contain constructs that suppress or obscure failures: bare `except:` clauses, `except Exception` without re-raise, or trivial `assert True`/`assert False` statements.

**Risk**: Tests that catch all exceptions silently or assert constant values provide false assurance. A passing test with a bare `except:` may be passing because it caught and swallowed the very failure it was meant to detect.

**Tolerable because**: Some constructs have legitimate uses (e.g., testing that *any* exception is raised). The finding flags their presence for review.

**Enforced by**: `QualityEvaluator` in `evaluators/quality.py`. Finding IDs: `bare-except-*`, `broad-except-*`, `trivial-assert-*`. Severity: MEDIUM.

---

## Acceptable Variability

The following are not constrained and do not produce findings:

- Test function naming conventions beyond the `test_` prefix.
- Choice of assertion library.
- File structure within the test directory.
- Number of tests per file.
- Use of async vs synchronous test functions.
- Docstring presence or style in test functions.
- Test execution order.
- Choice of mocking library (unittest.mock, pytest-mock, etc.) beyond presence detection.

---

## Mapping: Failure Class → Containment Check

The following table maps each OWASP LLM Top-10 failure class to the specific check that enforces containment evidence for it.

| Failure Class | Containment Evidence Required | Enforced By |
|---|---|---|
| Prompt Injection | Test names or content reference: `injection`, `inject`, `hijack`, `override_instruction` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Jailbreak | Test names or content reference: `jailbreak`, `dan`, `no_restriction` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Data Exfiltration | Test names or content reference: `exfiltrat`, `system_prompt`, `repeat_instructions` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Insecure Output | Test names or content reference: `xss`, `script`, `eval`, `unsafe_output` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Hallucination | Test names or content reference: `hallucin`, `fabricat`, `groundedness`, `factual` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Denial of Service | Test names or content reference: `dos`, `denial_of_service`, `long_input` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Bias | Test names or content reference: `bias`, `fairness`, `demographic` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Sensitive Information Disclosure | Test names or content reference: `sensitive`, `pii`, `secret`, `disclosure` | `AdversarialEvaluator` — `evaluators/adversarial.py` |
| Input boundary violation (corrupt inputs) | Chaos scenario `corrupt-inputs` passes | `CorruptInputExperiment` — `chaos/corrupt_inputs.py` |
| Credential boundary violation | Chaos scenario `security` passes | `SecurityChaosExperiment` — `chaos/security.py` |
| Infrastructure boundary violation | Chaos scenario `network` passes | `NetworkChaosExperiment` — `chaos/network.py` |

---

## How to Add a New Boundary

1. Define the constraint: state the unacceptable system state precisely.
2. Classify it: red line, tolerable-but-visible, or acceptable variability.
3. Identify the enforcement point: which module, class, or CLI flag enforces it.
4. Document it in this file under the appropriate section.
5. If no existing check covers it, add a `ValidationCriterion` in `core/validator.py` or a new chaos experiment in `chaos/`.
