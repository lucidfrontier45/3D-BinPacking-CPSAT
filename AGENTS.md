# AGENTS.md

Senior Python engineer. Zen of Python, type safety, `uv` for all tooling.

## Commands

| Task | Command |
| --- | --- |
| Type check + autofix | `uv run poe check` |
| Lint + autofix | `uv run poe lint` |
| Test | `uv run poe test` |
| Add dep | `uv add <package>` |

Run `uv run poe check` and `uv run poe lint` before finishing any task of Python file editting.

## Layout

- `src/bp_cpsat/` — source
- `tests/` — tests
- `pyproject.toml` — config, deps, poe tasks
- `uv.lock` — locked deps

## Style

- Type hints on every signature. No `Any`.
- PEP 8 / modern Python: f-strings, `pathlib` over `os.path`, specific exceptions (no bare `try-except`).

## Boundaries

- Ask before adding a library to `pyproject.toml`.
- Never use `pip` directly.
- Never delete or skip failing tests without being asked to refactor them.
