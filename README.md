# 3D-BinPacking-CPSAT

3D BinPacking solver built on the OR-Tools CP-SAT solver.

Given identical integer bins `(W, L, H)` and items with integer dimensions, the
solver packs every item with per-item rotation policy and minimizes the number
of bins used.

# Usage

```python
from bp_cpsat import Bin, Item, RotationType, Shape, solve, validate

bin_capacity = Bin(width=10, length=10, height=10)
items = [
    Item("a", Shape(6, 6, 6)),
    Item("b", Shape(4, 5, 6), RotationType.ALL),
    Item("c", Shape(8, 8, 4), RotationType.FIXED_BOTTOM),
]

solution = solve(items, bin_capacity)
assert solution is not None
validate(items, bin_capacity, solution)

print(solution.bin_count)  # proven minimum number of bins
for placement in solution.placements:
    print(placement.item_id, placement.bin_index, placement.origin.as_tuple())
```

`solve` returns `None` only when the instance is *proven* infeasible — for
example an item that cannot fit in one bin under its rotation policy.

## Optimality

`solve` searches `K` from a lower bound up to a greedy upper bound and stops at
the first feasible `K`. Feasibility is monotone in the number of identical
bins, so that `K` is the proven minimum. Check `solution.optimal` if you need
to distinguish a proof from a bounded-effort answer:

| `solution.optimal` | Meaning |
| --- | --- |
| `True` | `bin_count` is the proven minimum |
| `False` | A valid packing whose minimality was not proven before the time budget ran out |

A non-optimal result is still a fully valid packing — `validate` accepts it —
it is simply an upper bound on the minimum. Lowering `time_limit` trades
optimality guarantees for faster returns.

## Public API

| Name | Description |
| --- | --- |
| `Bin(width, length, height)` | Bin capacity, shared by all bins of an instance; a `Shape` |
| `Shape(width, length, height)` | Pure extent; `volume`, `base_area`, `fits_in`, `fits_beside` |
| `Coordinate(x, y, z)` | Non-negative point in bin space; `end(shape)`, `offset(...)`, `fits_box(...)` |
| `Item(id, shape, rotation)` | Item with `RotationType.NONE` / `FIXED_BOTTOM` / `ALL` |
| `Placement(item_id, bin_index, origin, shape)` | One placed box; `corner`, `fits_in(bin)`, `overlaps(other)` |
| `solve(items, bin, options=...)` | Minimum-bin search, returns `PackingSolution \| None` |
| `SolverOptions(...)` | Time limit, worker count, hints, validation, `ModelOptions` |
| `validate(items, bin, solution)` | Independent validator, raises `ValidationError` |
| `greedy_pack` / `best_greedy_pack` | Bottom-back-left heuristic (upper bound and hints) |
| `prepare` / `build_fixed_k_model` | Lower bounds and the fixed-K model, for benchmarking |

Every returned solution is checked by `validate` unless
`SolverOptions(verify=False)` is set.

The lower bound is the maximum of the volume bound and a greedy clique of the
pairwise incompatibility graph. The upper bound comes from a constructive
greedy packing, with `N` as the theoretical fallback.

`SolverOptions.time_limit` bounds the whole `[LB, UB]` search rather than each
fixed-K call, so total runtime does not grow with the width of the range. Use
`per_k_time_limit` to additionally cap each individual feasibility call.

`ModelOptions` exposes the strengthening constraints individually for
benchmarking. None of them change which packings are feasible, only how hard
they are to propagate. `full_reification` is off by default: it adds a
constraint per axis and direction per pair and measured consistently slower
than the default half reification, so it is kept switchable for reproducibility
rather than recommended.

Per-axis `Cumulative` relaxations and `NoOverlap2D` / `NoOverlap` global
constraints for axis-impossible subsets are not implemented yet; they remain
open items from #1.

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
