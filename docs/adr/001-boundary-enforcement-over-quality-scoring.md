# ADR 001: Boundary Enforcement Over Quality Scoring

**Status:** Accepted  
**Date:** 2024-01-01

---

## Context

The initial framing of shadow-architect described it as a "meta-testing framework that verifies, validates, and improves test strategies" using a weighted quality score (0–100). The primary output was a grade and a score derived from test metrics (assertion density, test type counts, coverage percentages).

This framing created several problems:

1. A passing score could coexist with unacceptable system states (e.g., no adversarial coverage on an AI product).
2. Score optimization became a proxy goal, displacing the actual goal of preventing high-impact failures.
3. The language of "quality" implied continuous improvement rather than hard stops.
4. Weighted scoring allowed partial credit for criteria that are binary safety gates.

---

## Decision Boundary

**This tool enforces system boundaries. It does not score quality.**

A passing result means: the defined boundary checks were not visibly violated. It does not mean the system is correct, high-quality, or safe in general.

The score field (`ValidationResult.score`) is retained as a compliance indicator — a convenience summary of how many weighted boundary checks passed — but it is not the primary output and must not be presented as a quality grade or safety rating.

---

## What Is Prevented

- Framing the tool as a quality assurance system
- Using the score as a delivery gate (e.g., "score ≥ 70 means ready to ship")
- Treating score improvement as equivalent to risk reduction
- Allowing a high score to override a failed gate condition (e.g., missing adversarial coverage)

---

## Rejected Alternatives

### Coverage metrics as primary output

**Rejected because:** Coverage percentage is a boundary gap indicator, not a boundary enforcement mechanism. A system with 100% symbol coverage and no adversarial checks is not safer than one with 60% coverage and full adversarial coverage. Optimizing for coverage metrics does not close the failure classes that matter most for AI systems.

**Failure mode of this alternative:** Teams optimize coverage numbers rather than closing the boundaries that prevent unacceptable states.

### Weighted scoring as the pass/fail mechanism

**Rejected because:** Weighted scoring allows partial credit for gate-level criteria. An AI product with no adversarial tests can still achieve a passing score if other criteria are met. This is not acceptable for gated decisions.

**Failure mode of this alternative:** Deployment gates are satisfied by metric manipulation rather than actual boundary coverage.

---

## Gating Conditions

This decision applies to all validation runs. The score field is informational; gate conditions are binary. A validation run is considered complete only when:

- All unacceptable-state boundaries have corresponding checks
- CRITICAL findings are resolved or explicitly overridden with documented justification

---

## Epistemic Honesty

**Known:** The boundary checks defined in this tool are not exhaustive. Passing all checks does not mean all boundaries hold.

**Assumed:** The boundaries defined in BOUNDARIES.md represent the most consequential failure classes for the systems this tool governs.

**Unverified:** Whether the boundary set is complete for all deployment contexts. Boundary definitions should be reviewed when system context changes significantly.

---

## Override Protocol

This framing can be overridden only by an explicit update to this ADR. Reverting to score-as-primary-output requires documenting why the boundary enforcement framing was insufficient and what failure mode it introduced.
