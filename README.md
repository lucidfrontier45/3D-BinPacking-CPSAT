# 3D-BinPacking-CPSAT

3D BinPacking solver built on the OR-Tools CP-SAT solver.

Given identical integer bins `(W, L, H)` and items with integer dimensions, the
solver packs every item with per-item rotation policy and minimizes the number
of bins used.

# Usage

```python
from bp_cpsat import Bin, Item, RotationType, solve, validate

bin_capacity = Bin(width=10, length=10, height=10)
items = [
    Item("a", 6, 6, 6),
    Item("b", 4, 5, 6, RotationType.ALL),
    Item("c", 8, 8, 4, RotationType.FIXED_BOTTOM),
]

solution = solve(items, bin_capacity)
assert solution is not None
validate(items, bin_capacity, solution)

print(solution.bin_count)  # proven minimum number of bins
for placement in solution.placements:
    print(placement.item_id, placement.bin_index, placement.x, placement.y, placement.z)
```

`solve` returns `None` when the instance is infeasible (for example an item
that cannot fit in one bin under its rotation policy) or when the time limit
runs out before a packing is found.

## Public API

| Name | Description |
| --- | --- |
| `Bin(width, length, height)` | Bin capacity, shared by all bins of an instance |
| `Item(id, width, length, height, rotation)` | Item with `RotationType.NONE` / `FIXED_BOTTOM` / `ALL` |
| `Placement` / `PackingSolution` | Immutable result objects, independent of OR-Tools |
| `solve(items, bin, options=...)` | Minimum-bin search, returns `PackingSolution \| None` |
| `SolverOptions(...)` | Time limit, worker count, hints, validation, `ModelOptions` |
| `validate(items, bin, solution)` | Independent validator, raises `ValidationError` |
| `greedy_pack` / `best_greedy_pack` | Bottom-left-back heuristic (upper bound and hints) |
| `prepare` / `build_fixed_k_model` | Lower bounds and the fixed-K model, for benchmarking |

`solve` searches `K` from a lower bound up to a greedy upper bound and stops at
the first feasible `K`, which is optimal because feasibility is monotone in the
number of identical bins. Every returned solution is checked by `validate`
unless `SolverOptions(verify=False)` is set.

The lower bound is the maximum of the volume bound and a greedy clique of the
pairwise incompatibility graph. The upper bound comes from a constructive
greedy packing, with `N` as the theoretical fallback.

With the default parallel search, equally optimal packings may differ between
runs. Set `SolverOptions(num_search_workers=1)` for bit-identical results.

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
