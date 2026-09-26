# 3D-BinPacking-CPSAT

3D BinPacking solver built on the OR-Tools CP-SAT solver.

# Install

Please first install the latest uv.
Then run the following command to install runtime libraries.

```bash
uv sync --no-dev
```

# Develop

```bash
uv sync
```

Project commands are defined in `pyproject.toml` and run with poethepoet.

```bash
uv run poe lint    # ruff check --fix .
uv run poe check   # ty check --fix .
uv run poe format  # ruff format .
uv run poe test    # pytest tests
```

# VSCode Settings

Install/activate all extensions listed in `.vscode/extensions.json`
