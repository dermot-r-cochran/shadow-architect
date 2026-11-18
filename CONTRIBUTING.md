# Contributing to shadow-architect

Contributions are welcome: bug reports, fixes, tests, documentation and focused improvements.

## Before you start

- For anything beyond a small fix, you may find it useful to open an issue first describing the problem and the change you have in mind, before you spend time on it.
- Read ADRs 001 to 005 and `docs/BOUNDARIES.md`. In short: this tool enforces boundaries and gates, it does not grade quality, and **no output, doc or docstring may claim correctness, completeness, exhaustiveness or safety** (ADR 004).
- A change to a check updates `docs/BOUNDARIES.md` in the same pull request.

## Making a change

- Keep a pull request to one change, and say in its description what it changes and why.
- Run what CI runs before you push:

```bash
pip install -e ".[dev]"
python -m compileall -q src
SHADOW_ARCHITECT_MOCK_AZURE=1 pytest --cov=shadow_architect --cov-fail-under=89
ruff check .
mypy src/
python .github/scripts/check_docs.py
```

- Every capability the README claims names the test that proves it, or says *no test yet* or *not yet implemented*. A new capability lands with its tests and its README row in the same pull request, and a renamed test updates the rows that cite it.
- The coverage threshold (89%) is a ratchet: it may rise with tests that earn it, never fall.
- A new evaluator lands with tests for both verdicts and a malformed-input case.
- No test needs live Azure credentials; `SHADOW_ARCHITECT_MOCK_AZURE=1` stands in for them.

## How a pull request is reviewed

The repository has one maintainer, Dermot Cochran, so a pull request may wait a while before anyone looks at it.

- CI must be green. A failing check is the first thing to fix.
- The review may be assisted by an AI tool, which reads the change and reports to the maintainer. It does not approve or merge anything.
- **Every outside pull request is merged by the maintainer, never by an automated process or an AI tool,** however small.
- A pull request may be declined, or asked to change shape, when it moves the project somewhere it is not meant to go. That is not a judgement on the work.

## Licence

Contributions are accepted under this repository's licence, the MIT License (`LICENSE`), the same terms everyone else receives the code under. No sign-off line and no contributor licence agreement are required. Only contribute work you have the right to license on these terms.

## Security

Please don't describe a security problem in a public issue or pull request. Report it privately instead, through the repository's **Security** tab (*Report a vulnerability*). Only the maintainer sees the report.
