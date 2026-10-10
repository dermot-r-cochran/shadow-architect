# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What this is

**shadow-architect** enforces system-level guardrails on AI systems deployed to Azure. It analyses Python test suites and system artefacts, surfaces constraint violations (missing adversarial coverage, absent isolation, unchecked failure modes), and gates decisions at defined boundaries — it is deliberately *not* a test-quality scorer (see ADR 001). Packaged as a library plus a Typer CLI (`shadow-architect`, entry point `shadow_architect.cli:app`). Python ≥3.10, `src/` layout.

## Commands

```bash
pip install -e ".[dev]"      # install with dev tools (pytest, pytest-cov, ruff, mypy)
pytest                       # run the suite (config in pyproject.toml: testpaths=tests, -v --tb=short)
pytest tests/test_validator.py                    # one file
pytest tests/test_validator.py::test_name         # one test
pytest --cov=shadow_architect --cov-fail-under=89 # what CI runs — coverage is a ratchet at 89%: raise it, never lower it
ruff check .                 # lint (line length 100; E, F, I, N, W, UP)
mypy src/                    # type check (strict mode)
python -m compileall -q src  # CI's parse gate — catches unparseable source even if no test imports it
python .github/scripts/check_docs.py  # CI's doc check — links, front matter, README test citations and module tree
```

CI (`.github/workflows/ci.yml`) runs the parse gate, pytest with the coverage ratchet on Python 3.10 and 3.13, `ruff check .`, and the doc check. Every README capability claim names the test that proves it, or says "not yet implemented" or "no test yet" — never cite a test that does not exist. The suite needs no live Azure credentials — set `SHADOW_ARCHITECT_MOCK_AZURE=1` to run any Azure-facing code without them. Testing mechanics, the incident the CI exists because of, and how to extend the suite are in `TestingStrategy.md`; two rules from it worth repeating: a new evaluator lands with tests for both verdicts plus a malformed-input case (the tool parses arbitrary user projects), and when editing docstrings replace rather than stack — stacked-duplicate docstrings once made four source files unparseable and killed the whole suite silently.

## Architecture

`src/shadow_architect/`:

- **`core/`** — the pipeline's spine: `models.py` (shared Pydantic models — Finding, Recommendation, TestSuite), `analyzer.py` (AST-based structural analysis of test suites), `validator.py` (boundary constraint enforcement — the criteria classes like `HasTestsCriterion` that produce pass/fail gates, not grades), `improver.py` (remediation plan generation), `reporter.py` (JSON + rich console output).
- **`evaluators/`** — `coverage.py` (untested symbols as uncovered boundaries), `quality.py` (anti-patterns that hide failures, e.g. bare `except`), `adversarial.py` (checks each OWASP LLM Top-10 failure class for containment evidence in the suite; absence is a finding).
- **`azure/`** — `client.py` (credential management, honours `SHADOW_ARCHITECT_MOCK_AZURE`), `storage.py` (Blob Storage report upload), `devops.py` (Test Plans + Work Items for CRITICAL/HIGH findings).
- **`chaos/`** — containment testing, not general resilience exploration (ADR 005): `base.py` (abstract `ChaosExperiment`: setup/execute/teardown, `AssertionError` in execute means the fault was *not* contained), three experiments (`corrupt_inputs.py`, `security.py`, `network.py`), `runner.py` (`ChaosRunner` orchestrator), `models.py` (ChaosResult/ChaosReport).
- **`cli.py`** — Typer commands: `run` (analyse + validate; `--fail-on critical|high` exits 1 on findings at that severity, `--fail-below` on the score), `generate-adversarial` (test stubs for uncovered failure classes), `upload` (report to Blob Storage), `chaos` (`--scenarios`, `--dry-run`).

## Governing ideas

The tool's identity is settled in the docs, and changes should stay inside it:

- **Boundary enforcement, not quality scoring** (ADR 001). A passing result means defined boundaries were not visibly violated — never present the score as a quality grade or safety rating. `ValidationResult.score` survives only as a compliance summary.
- **Gates, not recommendations** (ADR 002). Irreversible decisions (external AI exposure, agentic autonomy, releasing over CRITICAL findings) require the gate condition met or an explicit, recorded, time-bounded override — never silence.
- **Composition and emergence are first-class risks** for agentic systems (ADR 003); the question is whether impact is bounded, not whether each step is correct.
- **State what the tool does not claim** (ADR 004). No output proves correctness, exhaustiveness, or safety; keep docs, reports, and docstrings free of language implying otherwise.
- **Chaos experiments target a specific boundary each** (ADR 005) — corrupt-inputs (input containment), security (credential containment), network (infrastructure failures surfaced, not swallowed).

`docs/BOUNDARIES.md` is the concrete map from each boundary (red lines, tolerable-but-visible states, acceptable variability) to the specific criterion/evaluator/experiment enforcing it — when adding or changing a check, update it in the same change. `docs/STRATEGY.md` carries the full strategy context, including override and escalation protocols. Findings vocabulary throughout: a gap is a *containment boundary gap*, a chaos failure is a *finding*, not a measurement.

## Related repositories

The map of Dermot's public repositories and what crosses between them is
`RELATED-REPOSITORIES.md` in `dermot-r-cochran/star-rangers`; this section
names only this repository's own neighbours (added 2026-09-29 at his
direction). Nothing below shares code or data with this repository; what is
shared is stated exactly.

- **`dermot-r-cochran/architecture-definition-model`** is the nearest in
  subject: it defines and governs the architecture of generative-AI systems,
  where this tool enforces boundaries on them once deployed. Neither
  repository cites the other today; if one comes to, that is a relationship
  to record here and there.
- **Siblings by convention:** `careful-memory`, `world-model`, `foundation-model`,
  `shadow-architect`, `visual-llm`, `swarm`, `Voting` and
  `architecture-definition-model` all carry a `TestingStrategy.md` that keeps
  testing mechanics apart from the repository's rules; six run CI coverage as a
  ratchet at the measured baseline (`swarm`, `careful-memory`, `world-model`,
  `foundation-model`, `shadow-architect`, `visual-llm`); five keep
  architecture decision records with guard tests (`swarm`,
  `careful-memory`, `world-model`, `shadow-architect`, the ADM); here
  `tests/test_adr_guards.py` guards ADR 002 (gate on finding severity, not
  the score), and ADRs 001 and 003–005 do not yet have a guard test. When a
  convention here needs changing, those are the reference for how it is done
  in the account, and a change to the convention itself is worth landing in
  all of them or in none.
