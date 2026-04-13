# shadow-architect
AI-generated shadow architecture adversarial testing system

## Overview

**shadow-architect** is a meta-testing framework that **verifies**, **validates**, and **improves** existing test strategies and test frameworks for any specific use case, technical product, or AI capability hosted in **Azure Cloud**.

It analyses Python test suites to:

| Capability | Description |
|---|---|
| 📊 **Analyse** | Discover test counts, assertion density, mocks, fixtures, parametrisation, and test type coverage |
| ✅ **Validate** | Score the test suite against configurable quality criteria (0–100) |
| 🔍 **Evaluate** | Run symbol-level coverage estimation, anti-pattern detection, and adversarial category coverage |
| 🚀 **Improve** | Generate ranked, actionable recommendations with Azure-specific guidance |
| ☁️ **Azure integration** | Upload reports to Azure Blob Storage, publish results to Azure DevOps Test Plans, and create work items for findings |
| 🤖 **Adversarial stubs** | Auto-generate adversarial test stubs covering OWASP LLM Top-10 categories |

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
│   ├── analyzer.py      # Static test suite analysis (AST-based)
│   ├── validator.py     # Quality criteria validation with scoring
│   ├── improver.py      # Improvement plan generation
│   └── reporter.py      # JSON + rich console reporting
├── evaluators/
│   ├── coverage.py      # Symbol-level coverage estimation
│   ├── quality.py       # Anti-pattern detection (AST-based)
│   └── adversarial.py   # OWASP LLM Top-10 adversarial coverage checker
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

## Validation Criteria

| Criterion | Weight | Description |
|---|---|---|
| Has tests | 5.0 | Test suite contains at least one test function |
| Assertion density | 3.0 | Average assertions per test ≥ 1.0 |
| Unit tests | 4.0 | Unit test files detected |
| Integration tests | 3.0 | Integration test files detected |
| Adversarial tests | 4.0 | AI products must have adversarial/robustness tests |
| Security tests | 3.0 | API/cloud products must have security tests |
| Test isolation | 2.0 | Mocks/test-doubles used |
| Parametrised tests | 1.5 | pytest.mark.parametrize used |

Score = weighted sum of passed criteria, 0–100.

---

## Adversarial Categories (OWASP LLM Top-10)

The adversarial evaluator checks coverage of:

- Prompt Injection
- Jailbreak
- Data Exfiltration
- Insecure Output
- Hallucination
- Denial of Service
- Bias
- Sensitive Information Disclosure

---

## Azure Integration

| Service | Capability |
|---|---|
| Azure Blob Storage | Store and retrieve JSON test reports |
| Azure DevOps Test Plans | Publish test runs |
| Azure DevOps Work Items | Create Bugs for CRITICAL/HIGH findings |
| Azure Monitor | (recommended) Push metrics via OpenTelemetry |

Set `SHADOW_ARCHITECT_MOCK_AZURE=1` to run without live Azure credentials.

---

## Chaos Engineering

The `chaos` module provides **fault injection primitives** for resilience testing.
It is inspired by [IBM's Chaos Engineering overview](https://www.ibm.com/think/topics/chaos-engineering)
and covers three main scenarios:

| Scenario | What it tests |
|---|---|
| `corrupt-inputs` | Null injection, type confusion, encoding corruption, boundary values, malformed source, JSON corruption |
| `security` | Missing Azure credentials, RBAC 403/401 responses, expired tokens, wrong tenant/subscription |
| `network` | Latency injection, timeouts, connection refused, intermittent failures, slow responses |

### CLI usage

```bash
# Run all chaos scenarios
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

### Extending with custom experiments

```python
from shadow_architect.chaos import ChaosExperiment

class MyCustomExperiment(ChaosExperiment):
    name = "my-custom-fault"
    description = "Inject a custom fault condition"

    def setup(self) -> None:
        # Prepare fault injection (patch modules, set env vars, etc.)
        ...

    def execute(self) -> None:
        # Run your target under the fault condition.
        # Raise AssertionError to signal that the system did NOT handle
        # the fault gracefully.
        result = my_system_under_test()
        assert result.error_handled, "System did not handle the fault"

    def teardown(self) -> None:
        # Always called — restore normal state here.
        ...
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
