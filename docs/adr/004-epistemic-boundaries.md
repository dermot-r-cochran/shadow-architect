# ADR 004: Epistemic Boundaries

**Status:** Accepted  
**Date:** 2024-01-01

---

## Context

Testing and validation frameworks are frequently presented as evidence of correctness, safety, or completeness. This framing creates a false sense of assurance:

- A passing test suite is interpreted as evidence that the system is safe
- A high coverage score is interpreted as evidence that the system is correct
- A validation run with no CRITICAL findings is interpreted as clearance for deployment

For AI-enabled systems, this framing is particularly problematic because:
1. The space of inputs is effectively unbounded
2. Model behavior under adversarial inputs is not fully predictable from non-adversarial behavior
3. Emergent behavior in agentic pipelines cannot be enumerated in advance
4. Formal verification is infeasible for most AI system properties

---

## Decision Boundary

**This tool explicitly states what it does not claim.**

Every output from this tool — validation results, adversarial coverage reports, chaos experiment results — comes with an implicit epistemic boundary: the result is evidence about specific, defined checks under the conditions of the run. It is not proof of anything beyond that.

This decision requires that the tool's documentation, reports, and code-level docstrings avoid language that implies:
- Correctness ("the system works correctly")
- Completeness ("all cases are covered")
- Safety certification ("the system is safe")
- Exhaustiveness ("all failure modes have been checked")

---

## What Is Prevented

- Presenting validation scores as safety ratings
- Using test pass rates as proxies for system correctness
- Claiming that adversarial coverage is complete
- Framing a passing chaos experiment as proof of resilience rather than evidence of boundary compliance under the specific faults injected

---

## Rejected Alternatives

### Framing tests as approximations of proof

**Rejected because:** "Approximation of proof" implies a spectrum where more tests move the system closer to proven-correct. This framing is false for AI systems: no quantity of behavioral tests approximates a formal proof of a property that formal verification cannot establish. The framing also incentivizes coverage maximization as a proxy for safety, which is addressed in ADR 001.

**Failure mode of this alternative:** A team believes that increasing test coverage from 70% to 90% meaningfully reduces risk, when the risk is concentrated in adversarial input classes that are independent of symbol coverage.

### Omitting epistemic disclaimers to avoid appearing uncertain

**Rejected because:** False confidence is more dangerous than acknowledged uncertainty. A team that believes their system is certified safe because it passed a validation run is less likely to apply human judgment to deployment decisions than a team that understands the limits of what the run established.

**Failure mode of this alternative:** A deployment proceeds without human review because the validation score was interpreted as clearance.

---

## What the Tool Claims

The tool claims only:

1. The defined boundary checks were run against the test suite as it existed at the time of the run
2. The checks that passed indicate that the corresponding boundary conditions were not visibly violated under those checks
3. The findings reported are specific, defined violations — not a complete picture of all risks
4. The chaos experiments that passed indicate that the system handled the specific fault conditions injected — not that it handles all fault conditions

---

## Gating Conditions

This ADR does not define a gate. It defines the epistemic frame within which all other gates operate. The frame is:

> Passing a gate means the gate condition was met. It does not mean the system is safe, correct, or ready for arbitrary deployment.

---

## Epistemic Honesty (Applied to This ADR)

**Known:** The epistemic limits described here are well-established in software testing literature and are especially pronounced for AI systems.

**Assumed:** The primary consumers of this tool's output are people making deployment decisions, and those people benefit from explicit epistemic framing rather than implicit confidence.

**Unverified:** Whether the specific language choices in this tool's documentation are calibrated correctly to communicate uncertainty without undermining legitimate confidence in defined boundary checks.

---

## Override Protocol

The epistemic framing in this ADR cannot be overridden for individual runs. It is a property of the tool, not a configuration option. If a specific deployment context requires stronger claims about safety or correctness, those claims must be sourced from a separate process (e.g., formal verification, regulatory review) and are outside the scope of this tool.
