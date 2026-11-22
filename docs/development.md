# Development

## Requirements

- [uv](https://docs.astral.sh/uv/) (it installs Python 3.12 if needed; `requires-python >= 3.11`)
- No network access is needed at runtime, no environment variables, no secrets.

## Make targets

| Target | Command |
|---|---|
| `make` / `make help` | list targets |
| `make install` | `uv sync` |
| `make run` | `uv run streamlit run app.py` |
| `make test` | `uv run pytest -q` |
| `make lint` | `ruff check .` and `ruff format --check .` |
| `make format` | `ruff format .` and `ruff check --fix .` |
| `make typecheck` | `uv run mypy .` |
| `make check` | lint + typecheck + test |
| `make clean` | remove `__pycache__`, `.pytest_cache`, `.ruff_cache`, `.mypy_cache` |

## Dependencies

Runtime: `streamlit`, `matplotlib`, `pandas`. Dev: `pytest`, `ruff`, `mypy`. Versions are locked
in `uv.lock`.

## Code style

- Ruff with line length 100 and rule sets `E, F, I, UP, B, SIM`; formatted with `ruff format`.
- mypy with `disallow_untyped_defs`: every function, including tests, has type hints.
- `from __future__ import annotations` and modern syntax (`X | None`, `list[...]`).
- Frozen dataclasses for value objects; `Literal` types for modes and action kinds.
- Module and public-function docstrings; constants in `UPPER_CASE`; no mutable module state
  (read-only `MappingProxyType` for tables).
- No randomness anywhere.

## Adding things

- **A scenario:** write an ASCII map in `domain/scenarios.py`, a builder returning
  `_problem(parse_map(...))`, register it in `SCENARIOS`, and add a label in
  `app.py:SCENARIO_LABELS`. The parametrized tests pick it up automatically.
- **A rule:** write a function returning `RuleResult | None`, append it to `RULES` and its name
  to `RULE_ORDER`.
- **A strategy:** add a function in `reasoning/search.py` (reuse `_best_first` for
  priority-queue searches), a branch in `trace.run()`, and an entry in `app.py:ALGORITHM_KEYS`.

## Git workflow

- Conventional Commits (`chore:`, `feat(scope):`, `test:`, `docs:`, `fix:`), imperative mood,
  ≤ 72 characters, one milestone per commit.
- Before each commit: `git status`, `make check` green, Streamlit launch smoke test,
  `git diff --staged` review; files are staged by explicit path.
- No amending or force-pushing; corrections are new `fix:` commits.
- `.gitignore` excludes `.venv/`, caches, `.streamlit/secrets.toml` and editor/OS files.

History: run `git log --oneline`. It shows one commit per milestone, in order, starting from
`chore: scaffold uv project ...`. Later additions and fixes follow as separate `feat:`, `docs:`
and `fix:` commits.

Ruff is limited to `*.py` / `*.pyi` files (`[tool.ruff] include`), so the hand-aligned code
blocks in `docs/*.md` are left as written.
