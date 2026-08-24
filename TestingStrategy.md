# Testing Strategy

How shadow-architect is tested — written the day the suite came back from
being entirely unrunnable, which is itself the strategy's first lesson.

## The incident this document is built on

On 2026-08-24 the suite could not run at all: `pyproject.toml` carried a
duplicate `description` key (invalid TOML, which pytest and pip both refuse),
and four source files carried stacked-duplicate docstrings — an edited
docstring pasted in with the old text left attached to its closing quotes —
that made `analyzer.py`, `adversarial.py`, `coverage.py` and `quality.py`
unparseable. Every one of the 9 test files errored at collection, so the 150
tests proved nothing. All of it was fixed in the same change that added this
document; **139 tests now pass**.

The lesson is not about docstrings. It is that a suite nobody *runs
automatically* can be dead for an unknown length of time while looking, from
the file listing, comprehensively tested. Which makes the top item under
Known gaps the whole point.

## The suite (`tests/`, pytest — 139 tests across 9 files)

The tool's own vocabulary is boundary enforcement, and the suite maps onto
its components:

| File | Guards |
| --- | --- |
| `test_models.py` | the core data model (findings, severities, suites) |
| `test_validator.py` | boundary/constraint validation |
| `test_evaluators.py` | the evaluator set as a whole |
| `test_chaos.py` | chaos-style probes |
| `test_improver.py` | the improvement/generation path |
| `test_azure.py` | Azure-facing integration surfaces |
| `test_cli.py` | the Typer CLI |
| + 2 further files | remaining modules |

Run: `pip install -e ".[dev]"` (or `PYTHONPATH=src`) then `pytest`
(config in `pyproject.toml`). The suite runs without live Azure credentials —
Azure surfaces are tested at the boundary, not against the cloud.

## A fitting irony worth keeping

This tool's own evaluators detect vacuous tests, swallowed failures, and
uncovered boundaries in *other* projects (`quality.py`, `coverage.py`,
`adversarial.py`). Its own suite should therefore always clear its own bar:
run the evaluators against this repo's `tests/` when adding checks, and treat
any finding they raise here as a bug in one or the other.

## Extending

- A new evaluator lands with tests for both verdicts — the case it flags and
  the case it passes — plus at least one malformed-input case, since the tool
  parses arbitrary user projects.
- Docstring edits: replace, don't stack. The corruption pattern above came
  from leaving the old text attached to the new docstring's closing quotes,
  and it is invisible until something actually parses the file.

## Known gaps (candidates for next)

- **No CI — the incident above is the argument.** A minimal workflow
  (checkout, `pip install -e ".[dev]"` + pytest, plus
  `python -m compileall src` as a cheap parse gate) would have caught both
  the TOML and the docstring corruption on the day they were introduced. The
  `local-agent` repo's workflow is the closest template.
- 150 test functions exist but 139 run; the difference is worth an audit
  (skips/parametrisation vs. dead tests).
- Coverage unmeasured; ratchet it once CI exists.
