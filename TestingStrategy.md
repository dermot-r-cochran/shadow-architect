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

## The suite (`tests/`, pytest — 159 tests across 10 files)

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
| `test_adr_guards.py` | ADR guard tests — ADR 002 (`run --fail-on` gates on findings, not the score), ADR 004 (no string in `src/` and no output of a passing run claims correctness, completeness, safety or exhaustiveness) and ADR 005 (a dry run passes nothing; a FAILED experiment fails the command); ADR 001's guard is in `test_reporter.py`, ADR 003 has none yet |
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

Since 10 November 2026 CI does this on every run. The *Dogfood the gate* step
in `ci.yml` runs the README's own gate command on this repository through the
installed console script:
`shadow-architect run --suite shadow-architect --test-files tests/ --source-files src/ --fail-on high`.
A HIGH or CRITICAL finding fails the job. Setting it up found the first bug:
the README passes a suite as `--test-files tests/`, and a directory was read
as a file that held nothing, so this suite was reported as zero tests and the
`has-tests` red line. A directory now stands for every `.py` file under it
(`tests/test_cli.py`, `TestDirectoryArguments`). Two things the step does not
show. It declares no product context, as the README's example does not, so
the red lines that depend on one (R2 and R3 in `docs/BOUNDARIES.md`) are not
exercised; declared as an Azure product, this suite raises the HIGH
`security-tests-present` finding and the gate fails, which is recorded under
Known gaps. And the MEDIUM findings the tool raises here on that day, on two
conditions (no integration tests, and symbol coverage of 79.5% against the
80% floor), are tolerable-but-visible states that do not fail the gate.

## Extending

- A new evaluator lands with tests for both verdicts — the case it flags and
  the case it passes — plus at least one malformed-input case, since the tool
  parses arbitrary user projects.
- Docstring edits: replace, don't stack. The corruption pattern above came
  from leaving the old text attached to the new docstring's closing quotes,
  and it is invisible until something actually parses the file.

## The documentation check

Added 10 October 2026. The README's capability tables name, row by row, the
test that proves each claim (`tests/test_x.py::Class::test_name`), or say "not
yet implemented" or "no test yet". `.github/scripts/check_docs.py` (standard
library only, run by the `docs check` job in `ci.yml`) fails when:

- a relative link in README.md, CLAUDE.md, this file or `docs/` resolves to
  no file;
- a Markdown file carries a second front-matter block (the shape a stacked
  paste leaves — the same failure as the docstring incident, in prose);
- the README cites a test that does not exist, or its module tree under
  *Architecture* names a different set of modules than `src/shadow_architect/`
  holds.

Run it locally with `python .github/scripts/check_docs.py`. When a test the
README cites is renamed or removed, update the row in the same change.

## Known gaps (candidates for next)

- ~~No CI~~ — **closed 2026-08-24, the day after this document argued for
  it**: `.github/workflows/ci.yml` runs `python -m compileall src` (the parse
  gate that would have caught the incident on day one), pytest on Python
  3.10/3.13 with a coverage ratchet at the measured 89% baseline, and a
  `ruff check .` job — added green, the outstanding 32 findings fixed in the
  same change. One of those findings was a real bug, not style: the CLI
  computed the coverage evaluation and then discarded it, so reports silently
  omitted every symbol-gap finding; `cli.py` now merges
  `coverage_result.findings` like its adversarial and quality neighbours.
- ~~No type check in CI~~ — **closed 2026-10-19**: `mypy src/` (strict, as
  configured in `pyproject.toml`) runs as the `mypy` job in `ci.yml`, added
  green after annotation-only fixes to the context-manager `__exit__` return
  types in `chaos/` and the experiment list in `cli.py`.
- ~~150 test functions exist but 139 run; the difference is worth an audit
  (skips/parametrisation vs. dead tests)~~ — **audited 2026-10-19**: no
  dead tests. The surplus is `def test_…` lines written *inside* fixture
  source strings (the sample suites the tests feed the analyzer); a plain
  grep counts them, pytest does not. The same audit found the analyzer
  itself counting every test method of a `Test*` class twice (`ast.walk`
  visits the method, then a class branch counted it again), so the tool
  reported 19 tests for this repository's `tests/test_cli.py` where pytest
  collects 9; fixed in `core/analyzer.py`, pinned by
  `tests/test_analyzer.py::TestStrategyAnalyzerBasic::test_class_based_tests_are_counted_once`.
- ~~Coverage unmeasured~~ — the CI ratchet above holds it at ≥89%.
- **Open, found 2026-11-10 by the dogfood step:** run with `--product Azure`
  (the tool has an Azure integration), this suite raises the HIGH
  `security-tests-present` finding, because test types are read from file
  names and no test file here is named for security or auth. The dogfood step
  declares no product, so it does not meet this. By the rule above it is a
  bug in one or the other; which one is not yet decided.
- **Open, found the same day:** the console lists the validator's findings
  only. A finding raised by the analyzer or an evaluator alone
  (`syntax-error-*`, `missing-file-*`, `adversarial-gaps`,
  `low-symbol-coverage`, the anti-pattern findings) is in the JSON report but
  not on screen, so `--fail-on high` can exit 1 without the console naming
  the finding that tripped it.
