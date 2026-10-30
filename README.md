# shadow-architect
System-level guardrail enforcement for AI systems on Azure Cloud

## What This Repository Is For

This repository documents system boundaries, decision gates, and constraints for AI-enabled systems.

It is not intended to:
- prove correctness,
- exhaustively test behavior,
- or certify safety in the abstract.

Instead, it exists to make explicit:
- which failures are unacceptable,
- which decisions are irreversible,
- and where human judgment is required before proceeding.

Tests, checks, and reviews referenced here exist to enforce these boundaries empirically when formal guarantees are infeasible.

**shadow-architect** enforces system-level guardrails on AI systems. It is not a test quality scorer. It does not measure coverage percentages or rank delivery velocity. It exists to surface constraint violations, gate decisions at defined boundaries, and make failure modes visible before they become irreversible.

It operates on Python test suites and system artefacts to:

| Capability | Description | Proved by |
|---|---|---|
| 🔍 **Analyse** | Detect structural gaps: missing adversarial coverage, absent isolation boundaries, unchecked failure modes | `tests/test_analyzer.py::TestStrategyAnalyzerBasic::test_ai_product_recommends_adversarial_tests`, `tests/test_analyzer.py::TestStrategyAnalyzerBasic::test_empty_suite_produces_no_tests_finding` |
| 🚧 **Enforce boundaries** | Check whether declared system constraints are violated — not whether a score threshold is met | `tests/test_validator.py::TestTestValidator::test_adversarial_criterion_applicable_to_ai_product` |
| ⚠️ **Surface failure classes** | Identify which OWASP LLM Top-10 failure classes are uncontained in the current suite | `tests/test_evaluators.py::TestAdversarialEvaluator::test_empty_suite_flags_all_categories` |
| 🔒 **Gate decisions** | Block or escalate when irreversible, externally-visible, or autonomy-expanding decisions lack required evidence | `tests/test_adr_guards.py::TestAdr002GatingOnFindingsNotScore::test_fail_on_high_blocks_ai_product_without_adversarial_tests` |
| ☁️ **Azure integration** | Upload constraint-violation reports to Azure Blob Storage; create work items for CRITICAL/HIGH findings in Azure DevOps | `tests/test_azure.py::TestStorageClient::test_upload_report_returns_blob_name`, `tests/test_azure.py::TestDevOpsClient::test_create_work_items_for_high_findings` |
| 🤖 **Containment stubs** | Generate test stubs for uncovered adversarial failure classes | `tests/test_cli.py::TestGenerateAdversarialCommand::test_generates_stubs_to_file` |

Every row in this README that claims a capability names the test that proves it (file and test name), or says "not yet implemented", or "no test yet"; `.github/scripts/check_docs.py` fails CI if a named test does not exist.

---

## System Boundaries and Red Lines

These are the constraints this tool enforces. They are not advisory: each violation is a finding in every report, and `--fail-on` (off by default) turns findings at or above a chosen severity into a failed run.

| Category | State | Classification |
|---|---|---|
| No tests present | System has zero test functions | **Red line** — unacceptable |
| No adversarial coverage | AI/LLM product with no adversarial or robustness tests | **Red line** — unacceptable |
| No security tests | API/cloud product with no authentication or authorisation tests | **Red line** — unacceptable |
| Unparseable test files | A declared test file has a syntax error | **Red line** — unacceptable |
| Missing test isolation | External services called directly without mocking | **Tolerable but must be visible** |
| Low symbol coverage | Source symbols not referenced in any test | **Tolerable but must be visible** |
| Missing integration tests | No cross-component boundary checks | **Tolerable but must be visible** |
| No parametrised tests | No boundary-value or equivalence-class coverage | **Tolerable but must be visible** (LOW) |

Detailed boundary definitions are in [`docs/BOUNDARIES.md`](docs/BOUNDARIES.md).

---

## Decisions Subject to Gating

The following decisions are gated. This tool enforces or surfaces the gate condition. They cannot proceed on advisory review alone.

| Decision | Gate Condition |
|---|---|
| Deploying an AI capability to external users | Adversarial test coverage must include prompt injection, data exfiltration, and insecure output categories |
| Enabling agentic autonomy (write/execute/publish) | Human decision gate must be explicit in code; containment experiments must have passed |
| Releasing after a validation run with CRITICAL findings | Not permitted without explicit override — see [Override and Escalation Protocols](#override-and-escalation-protocols) |
| Exposing an endpoint that processes untrusted input | Security test presence check must pass |

These are gates, not recommendations. A passing score does not override a failed gate condition.


---

## Failure Classes and Containment Boundaries

The adversarial evaluator checks whether each OWASP LLM Top-10 failure class has containment evidence in the test suite. Absence is a finding, not a recommendation.

| Failure Class | Containment Check |
|---|---|
| Prompt Injection | Tests verify the system refuses or ignores injected instructions |
| Jailbreak | Tests verify the system stays within its declared behaviour envelope |
| Data Exfiltration | Tests verify system prompts and training data are not disclosed |
| Insecure Output | Tests verify output cannot execute or harm downstream consumers |
| Hallucination | Tests verify the system acknowledges uncertainty rather than fabricating |
| Denial of Service | Tests verify oversized or malformed inputs are rejected within resource limits |
| Bias | Tests verify responses do not exhibit demographic or representational skew |
| Sensitive Information Disclosure | Tests verify PII, secrets, and internal configuration are not disclosed |

A gap in any of these categories is a containment boundary gap, not a coverage gap.


---

## Evidence We Require Before Release

The following must be present and passing before a release gate opens:

- At least one test function exists in the declared suite.
- For AI/LLM products: adversarial containment tests cover prompt injection and data exfiltration failure classes at minimum.
- For API/cloud products: authentication, authorisation, and input-validation tests are present.
- Chaos containment scenarios (corrupt-inputs, security, network) pass for the critical path.
- No CRITICAL constraint violations are reported by `shadow-architect run`.
- Any CRITICAL or HIGH finding that was overridden is recorded with owner and rationale.

Evidence is empirical, not declarative. Stating that a boundary holds is not evidence that it holds.


---

## What This Strategy Does NOT Claim

This strategy does not attempt to:

- **Prove correctness.** Tests are empirical enforcement of boundaries, not approximations of proof. A passing gate means the declared constraints were not visibly violated, not that the system is correct.
- **Exhaustively test behaviour.** The strategy targets failure classes at boundaries, not all possible inputs. Test coverage is not a proxy for safety, and untested behaviour exists regardless of score.
- **Certify safety in the abstract.** No score, grade, or passing result is a safety certificate.
- **Encode ethics or values.** The bias and sensitive-disclosure checks enforce observable boundary conditions, not ethical judgements or a complete ethical framework.
- **Guarantee predictable behaviour in agentic systems.** Composition and emergent behaviour are primary risks that static checks cannot fully enumerate.
- **Replace runtime monitoring.** Static analysis and offline test suites cannot detect all runtime failure modes. This tool is a pre-release gate, not a substitute for observability.

Where formal verification is infeasible, this tool provides empirical boundary enforcement. Testing is evidence, not proof.


---

## Override and Escalation Protocols

A gate can be overridden only under the following conditions (the protocol of [ADR 002](docs/adr/002-gating-authority-for-irreversible-decisions.md)):

1. The override is explicit — not implied by silence, skip, or configuration change
2. The person accepting the override acknowledges the specific risk in writing (commit message, PR description, or linked issue)
3. The override is time-bounded — it applies to a named release or deployment, not indefinitely
4. The override is visible in the audit trail — it must appear in the validation report metadata
5. Override authority cannot be self-assigned — the override is accepted by the person responsible for boundary definition for the affected system, and an override of a red-line constraint escalates: it cannot be closed by the person who opened it

Override does not remove the gate. It records that the gate was bypassed and by whom.

If a CRITICAL finding exists and cannot be resolved, the deployment is escalated to a human decision. The tool surfaces the finding; it does not make the deployment decision.

---

## Containment Testing

The `chaos` module enforces containment boundaries under adverse conditions. It is not general resilience exploration — each experiment targets a specific boundary:

| Experiment | Boundary Enforced | Proved by |
|---|---|---|
| `corrupt-inputs` | System must handle malformed, null, and adversarial inputs without uncontrolled failure | `tests/test_chaos.py::TestCorruptInputExperiment::test_unhandled_exception_causes_failure` |
| `security` | System must not silently succeed when credentials are missing, expired, or insufficient | `tests/test_chaos.py::TestSecurityChaosExperiment::test_sensitive_leak_detection` |
| `network` | System must surface failures from latency, timeout, and connection disruption — not swallow them | `tests/test_chaos.py::TestNetworkChaosExperiment::test_unhandled_network_exception_fails` |

An experiment **passes** when the system isolates the fault and surfaces it cleanly. It **fails** (returns `FAILED` status) when the fault propagates, causes silent data corruption, or is swallowed without visibility: the boundary was crossed. This is a finding, not a measurement.

### CLI usage

```bash
# Run all containment scenarios
shadow-architect chaos

# Run specific scenarios only
shadow-architect chaos --scenarios corrupt-inputs,network

# Focus on a specific module
shadow-architect chaos \
  --scenarios corrupt-inputs,security,network \
  --target-module src/shadow_architect/core/analyzer.py \
  --output-json chaos_report.json

# Dry-run: list experiments without executing
shadow-architect chaos --dry-run
```

### Programmatic usage

```python
from shadow_architect.chaos import (
    ChaosRunner,
    CorruptInputExperiment,
    NetworkChaosExperiment,
    SecurityChaosExperiment,
)

runner = ChaosRunner([
    CorruptInputExperiment(target=my_function, sample_input="hello"),
    NetworkChaosExperiment(target=my_api_call),
    SecurityChaosExperiment(target=my_azure_call),
])
report = runner.run()
runner.print_report(report)
```

### Extending with custom containment experiments

```python
from shadow_architect.chaos import ChaosExperiment

class MyCustomExperiment(ChaosExperiment):
    name = "my-custom-fault"
    description = "Verify the system contains a custom fault class"

    def setup(self) -> None:
        # Establish the fault condition (patch modules, set env vars, etc.)
        ...

    def execute(self) -> None:
        # Run the system under the fault condition.
        # Raise AssertionError to signal the system did NOT contain the fault.
        result = my_system_under_test()
        assert result.error_handled, "Fault was not contained — propagation detected"

    def teardown(self) -> None:
        # Always called — restore normal state here.
        ...
```

---

## Quick Start

### Installation

```bash
pip install -e ".[dev]"
```

### Analyse a test suite

```bash
shadow-architect run \
  --suite "My AI Service" \
  --product "Azure OpenAI Chat" \
  --use-case "Conversational AI" \
  --test-files tests/test_chat.py \
  --test-files tests/test_integration.py \
  --source-files src/chat.py \
  --source-files src/utils.py \
  --output-json report.json
```

### Fail CI when score is below a threshold

```bash
shadow-architect run --suite "My Service" --test-files tests/ --fail-below 70
```

[ADR 001](docs/adr/001-boundary-enforcement-over-quality-scoring.md) forbids using this score as a delivery gate; to gate CI on the findings themselves, use `--fail-on` below.

### Gate CI on constraint violations

```bash
# exit 1 if any finding is HIGH or above (or: --fail-on critical); off by default
shadow-architect run --suite "My Service" --test-files tests/ --fail-on high
```

### Generate adversarial test stubs

```bash
shadow-architect generate-adversarial \
  --suite "AI Capability" \
  --product "Azure OpenAI GPT-4" \
  --use-case "Chatbot" \
  --output tests/test_adversarial_generated.py
```

### Upload a report to Azure Blob Storage

```bash
# Set credentials via environment variables
export AZURE_STORAGE_ACCOUNT_URL="https://<account>.blob.core.windows.net"
shadow-architect upload report.json --suite "My AI Service"
```

---

## Architecture

```
shadow_architect/
├── core/
│   ├── models.py        # Shared data models (Finding, Recommendation, TestSuite, …)
│   ├── analyzer.py      # Static boundary detection and structural analysis (AST-based)
│   ├── validator.py     # Boundary constraint enforcement; score kept only as a compliance summary (ADR 001)
│   ├── improver.py      # Boundary enforcement recommendation generation
│   └── reporter.py      # JSON + rich console reporting
├── evaluators/
│   ├── coverage.py      # Boundary gap detection (untested symbols as uncovered boundaries)
│   ├── quality.py       # Constraint violation detection (anti-pattern checks)
│   └── adversarial.py   # Failure class and containment boundary checker
├── azure/
│   ├── client.py        # Azure credential management
│   ├── storage.py       # Azure Blob Storage integration
│   └── devops.py        # Azure DevOps Test Plans & Work Items
├── chaos/
│   ├── models.py        # ChaosResult / ChaosReport Pydantic models
│   ├── base.py          # Abstract ChaosExperiment base class
│   ├── corrupt_inputs.py# InputCorruptor + CorruptInputExperiment
│   ├── security.py      # PermissionChaos + SecurityChaosExperiment
│   ├── network.py       # NetworkChaos + NetworkChaosExperiment
│   └── runner.py        # ChaosRunner orchestrator
└── cli.py               # Typer-based CLI
```

---

## Azure Integration

| Service | Use | Proved by |
|---|---|---|
| Azure Blob Storage | Store constraint-violation reports | `tests/test_azure.py::TestStorageClient::test_upload_report_returns_blob_name` |
| Azure DevOps Test Plans | Publish gate results | `tests/test_azure.py::TestDevOpsClient::test_publish_test_run_returns_dict` |
| Azure DevOps Work Items | Create Bugs for CRITICAL/HIGH constraint violations | `tests/test_azure.py::TestDevOpsClient::test_create_work_items_for_high_findings` |
| Azure Monitor | (recommended) Push boundary metrics via OpenTelemetry | not yet implemented |

Set `SHADOW_ARCHITECT_MOCK_AZURE=1` to run without live Azure credentials.

---

## Running Tests

```bash
pip install -e ".[dev]"
pytest
```

---

## Development

```bash
# Lint
ruff check src/ tests/

# Type check (strict; CI runs this too)
mypy src/
```
