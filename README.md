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

| Capability | Description |
|---|---|
| 🔍 **Analyse** | Detect structural gaps: missing adversarial coverage, absent isolation boundaries, unchecked failure modes |
| 🚧 **Enforce boundaries** | Check whether declared system constraints are violated — not whether a score threshold is met |
| ⚠️ **Surface failure classes** | Identify which OWASP LLM Top-10 failure classes are uncontained in the current suite |
| 🔒 **Gate decisions** | Block or escalate when irreversible, externally-visible, or autonomy-expanding decisions lack required evidence |
| ☁️ **Azure integration** | Upload constraint-violation reports to Azure Blob Storage; create work items for CRITICAL/HIGH findings in Azure DevOps |
| 🤖 **Containment stubs** | Generate test stubs for uncovered adversarial failure classes |

---

## System Boundaries and Red Lines

Boundaries fall into three categories:

### (a) Unacceptable States — Must Never Occur

These are hard stops. No deployment, escalation path, or override process compensates for reaching these states:
### Enforce boundaries on a test suite

- Prompt injection achieving instruction override in a deployed AI capability
- Sensitive data (PII, credentials, system prompts) disclosed via model output
- Agentic system taking irreversible external action (write, delete, publish, execute) without a confirmed human decision gate
- Unsafe model output (executable code, injection payloads) reaching a downstream consumer without sanitisation

These are enforced by the adversarial evaluator and security containment checks. A validation run that leaves any of these unchecked does not pass.
### Gate CI on constraint violations

### (b) Risky but Tolerable — Must Be Visible and Bounded

These states are permitted under monitored conditions with defined containment:
### Generate containment stubs for uncovered failure classes

- Hallucination or factual error in low-stakes, non-binding output — tolerable if grounded response is not claimed
- Integration test absence in early-stage development — tolerable if the boundary is declared and tracked as a finding
- Missing mock isolation — tolerable in small suites (≤5 tests), must be surfaced as a finding in larger ones
- Partial adversarial category coverage — tolerable only if uncovered categories are explicitly deferred, not silently absent

These states are surfaced as findings with MEDIUM or HIGH severity. They do not block all deployments but must be acknowledged.

### (c) Acceptable Variability

These are expected to vary without requiring escalation:

- Assertion density variation across test types
- Test file naming conventions
- Coverage percentages in source files not declared as boundary-critical
- Choice of mocking library or fixture style
```bash
export AZURE_STORAGE_ACCOUNT_URL="https://<account>.blob.core.windows.net"
shadow-architect upload report.json --suite "My AI Service"
```

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

The adversarial evaluator checks coverage across failure classes relevant to LLM and agentic systems. These are not checklist items — they are categories of containment failure:

| Failure Class | Containment Boundary |
|---|---|
| **Prompt Injection** | Model must not execute injected instructions; boundary is instruction integrity |
| **Jailbreak** | Model must not bypass its defined behavioral constraints |
| **Data Exfiltration** | System prompt, training data, and PII must not be surfaced via model output |
| **Insecure Output** | Executable or injection-capable content must not reach downstream consumers |
| **Hallucination** | Model must not present fabricated facts as verified; boundary is epistemic honesty |
| **Denial of Service** | Resource consumption must be bounded; requests beyond limits must be rejected |
| **Bias** | Responses must not reinforce demographic or group-based harm |
| **Sensitive Information Disclosure** | PII, credentials, and internal configuration must not be disclosed |

A gap in any of these categories is a containment boundary gap, not a coverage gap.

---

## Evidence We Require Before Release

Before a system governed by this tool is released, the following must be present and documented:

1. A completed validation run with no CRITICAL findings unresolved
2. Adversarial coverage for all high-severity failure classes (prompt injection, data exfiltration, insecure output, sensitive info disclosure)
3. Security test presence for any system handling untrusted input or external credentials
4. Containment experiment results showing that corrupt-input, security-permission, and network-disruption scenarios do not produce unhandled failures
5. An explicit record of any overridden gate, including who accepted the risk and under what conditions

Evidence is empirical, not declarative. Stating that a boundary holds is not evidence that it holds.

---

## What This Strategy Does NOT Claim

This tool does not:

- **Prove correctness.** Passing validation means defined boundaries were enforced. It does not mean the system behaves correctly in all cases.
- **Exhaustively test behavior.** Test coverage is not a proxy for safety. Untested behavior exists regardless of score.
- **Certify safety in the abstract.** No score, grade, or passing result is a safety certificate.
- **Encode ethics or values.** The bias and sensitive disclosure checks probe for specific failure classes. They do not encode a complete ethical framework.
- **Guarantee predictable behavior in agentic systems.** Composition and emergent behavior are primary risks that static checks cannot fully enumerate.

Where formal verification is infeasible, this tool provides empirical boundary enforcement. Testing is evidence, not proof.

---

## Override and Escalation Protocols

A gate can be overridden only under the following conditions:

1. The override is explicit — not implied by silence, skip, or configuration change
2. The person accepting the override acknowledges the specific risk in writing (commit message, PR description, or linked issue)
3. The override is time-bounded — it applies to a named release or deployment, not indefinitely
4. The override is visible in the audit trail — it must appear in the validation report metadata

Override does not remove the gate. It records that the gate was bypassed and by whom.

If a CRITICAL finding exists and cannot be resolved, the deployment is escalated to a human decision. The tool surfaces the finding; it does not make the deployment decision.

---

## Containment Testing

The `chaos` module enforces containment boundaries under adverse conditions. It is not general resilience exploration — each experiment targets a specific boundary:

| Experiment | Boundary Enforced |
|---|---|
| `corrupt-inputs` | System must handle malformed, null, and adversarial inputs without uncontrolled failure |
| `security` | System must not silently succeed when credentials are missing, expired, or insufficient |
| `network` | System must surface failures from latency, timeout, and connection disruption — not swallow them |

A containment experiment that fails (returns `FAILED` status) indicates the boundary was crossed. This is a finding, not a measurement.
```
shadow_architect/
├── core/
│   ├── models.py        # Shared data models (Finding, Recommendation, TestSuite, …)
│   ├── analyzer.py      # Static analysis — detects structural gaps and missing boundaries
│   ├── validator.py     # Boundary constraint enforcement — pass/fail, not scored
│   ├── improver.py      # Constraint remediation plan generation
│   └── reporter.py      # JSON + rich console reporting
├── evaluators/
│   ├── coverage.py      # Symbol-level gap detection (unchecked components)
│   ├── quality.py       # Anti-pattern detection (constructs that hide failures)
│   └── adversarial.py   # Failure class coverage: OWASP LLM Top-10 containment check
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

## System Boundaries and Red Lines

These are the constraints this tool enforces. They are not advisory. Violations at the CRITICAL level gate release.

| Category | State | Classification |
|---|---|---|
| No tests present | System has zero test functions | **Red line** — unacceptable |
| No adversarial coverage | AI/LLM product with no adversarial or robustness tests | **Red line** — unacceptable |
| No security tests | API/cloud product with no authentication or authorisation tests | **Red line** — unacceptable |
| Missing test isolation | External services called directly without mocking | **Tolerable but must be visible** |
| Low symbol coverage | Source symbols not referenced in any test | **Tolerable but must be visible** |
| Missing integration tests | No cross-component boundary checks | **Tolerable but must be visible** |
| No parametrised tests | No boundary-value or equivalence-class coverage | Acceptable variability |

Detailed boundary definitions are in [`docs/BOUNDARIES.md`](docs/BOUNDARIES.md).

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

---

## Decisions Subject to Gating

The following decision classes are **gated**: release is blocked unless the required evidence is present.

1. **Irreversible decisions** — Any action that cannot be rolled back (e.g., data deletion, tenant-level configuration changes). Requires explicit adversarial and isolation test evidence before gate passes.
2. **External exposure** — Any component that accepts or emits data across a trust boundary (API endpoints, LLM prompt construction, output rendering). Requires security and insecure-output containment evidence.
3. **Agentic autonomy expansion** — Any change that increases an agent's capability scope, tool access, or action authority. Requires adversarial coverage of the new capability class before gate passes.
4. **Non-rollbackable failure modes** — Failure modes that cannot be silently rolled back (credential leakage, schema mutations, irreversible external writes). These trigger escalation regardless of overall constraint score.

Gating is enforced via `--fail-below` in CI. The default gate threshold is documented in [`docs/STRATEGY.md`](docs/STRATEGY.md).

---

## Evidence We Require Before Release

The following must be present and passing before a release gate opens:

- At least one test function exists in the declared suite.
- For AI/LLM products: adversarial containment tests cover prompt injection and data exfiltration failure classes at minimum.
- For API/cloud products: authentication, authorisation, and input-validation tests are present.
- Chaos containment scenarios (corrupt-inputs, security, network) pass for the critical path.
- No CRITICAL constraint violations are reported by `shadow-architect run`.
- Any CRITICAL or HIGH finding that was overridden is recorded with owner and rationale.

---

## Override and Escalation Protocols

Gating decisions can be overridden under the following conditions:

1. **Who can override**: The person responsible for boundary definition for the affected system. Override authority cannot be self-assigned.
2. **What is required**: A written rationale explaining why the constraint does not apply or why the risk is accepted, linked to the finding ID in the report.
3. **Visibility**: All overrides are recorded in the Azure DevOps work item created for the finding. Overrides without a recorded rationale invalidate the gate.
4. **Escalation trigger**: Any override of a RED LINE constraint (unacceptable state) escalates automatically — it cannot be closed by the same person who opened the override.
5. **Expiry**: Overrides do not carry forward across releases. Each release gate requires fresh evidence or a fresh override.

---

## Failure Classes We Intentionally Ignore

This strategy does not attempt to:

- **Prove correctness.** Tests are empirical enforcement of boundaries, not approximations of proof. A passing gate means the declared constraints were not visibly violated, not that the system is correct.
- **Exhaustively test behaviour.** The strategy targets failure classes at boundaries, not all possible inputs. Combinatorial exhaustion is not the goal.
- **Encode ethics or values.** The bias and sensitive-disclosure checks enforce observable boundary conditions, not ethical judgements. Where formal verification is infeasible, we test boundary enforcement empirically.
- **Replace runtime monitoring.** Static analysis and offline test suites cannot detect all runtime failure modes. This tool is a pre-release gate, not a substitute for observability.

---

## Chaos Engineering: Containment Testing

The `chaos` module validates **resilience boundaries** — whether the system contains and surfaces failures gracefully rather than propagating or silently swallowing them.

| Scenario | Boundary Tested |
|---|---|
| `corrupt-inputs` | Input validation boundary: null injection, type confusion, encoding corruption, malformed source |
| `security` | Credential and authorisation boundary: missing credentials, RBAC responses, expired tokens |
| `network` | Infrastructure boundary: latency, timeouts, connection failure, intermittent disruption |

A chaos experiment **passes** when the system isolates the fault and surfaces it cleanly. It **fails** when the fault propagates, causes silent data corruption, or is swallowed without visibility.

### CLI usage

```bash
# Run all containment experiments
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
│   ├── validator.py     # Boundary constraint enforcement with compliance scoring
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

| Service | Capability |
|---|---|
| Azure Blob Storage | Store and retrieve JSON reports |
| Azure DevOps Test Plans | Publish validation runs |
| Azure DevOps Work Items | Create Bugs for CRITICAL/HIGH findings |
| Azure Monitor | (recommended) Push metrics via OpenTelemetry |
## Azure Integration

| Service | Use |
|---|---|
| Azure Blob Storage | Store constraint-violation reports |
| Azure DevOps Test Plans | Publish gate results |
| Azure DevOps Work Items | Create Bugs for CRITICAL/HIGH constraint violations |
| Azure Monitor | (recommended) Push boundary metrics via OpenTelemetry |

Set `SHADOW_ARCHITECT_MOCK_AZURE=1` to run without live Azure credentials.

---

## Installation

```bash
pip install -e ".[dev]"
```

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

# Type check
mypy src/
```
