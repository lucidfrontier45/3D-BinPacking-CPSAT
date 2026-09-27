"""Pack 100 random sized items into identical ``(100, 100, 70)`` bins.

Run it with::

    uv run python examples/pack_random_items.py

The JSON packing result is written to ``packing_result.json`` by default; use
``-o`` to choose another file. ``-n`` sets how many items to generate and
``--seed`` makes the random generation reproducible::

    uv run python examples/pack_random_items.py -n 50 --seed 42 -o out.json
"""

from __future__ import annotations

import argparse
import json
import random
from collections.abc import Sequence
from pathlib import Path

from bp_cpsat import (
    Bin,
    Item,
    PackingSolution,
    RotationType,
    Shape,
    SolverOptions,
    solve,
    validate,
)

BIN_CAPACITY = Bin(width=100, length=100, height=70)
DEFAULT_ITEM_COUNT = 100
DEFAULT_SEED = 0
MIN_SIDE = 10
MAX_SIDE = 40


def make_items(count: int, seed: int) -> list[Item]:
    """Build ``count`` items with random integer sides that each fit in one bin."""
    rng = random.Random(seed)
    return [
        Item(
            id=f"item-{index:03d}",
            shape=Shape(
                width=rng.randint(MIN_SIDE, MAX_SIDE),
                length=rng.randint(MIN_SIDE, MAX_SIDE),
                height=rng.randint(MIN_SIDE, MAX_SIDE),
            ),
            rotation=RotationType.ALL,
        )
        for index in range(count)
    ]


def to_json(solution: PackingSolution, bin_capacity: Bin) -> list[dict[str, object]]:
    """Group placements by bin into a JSON-ready list of bin records."""
    by_bin: dict[int, list[dict[str, object]]] = {}
    for placement in solution.placements:
        by_bin.setdefault(placement.bin_index, []).append(
            {
                "item_id": placement.item_id,
                "origin": placement.origin.as_tuple(),
                "shape": placement.shape.as_tuple(),
            }
        )
    return [
        {
            "bin_shape": bin_capacity.as_tuple(),
            "placements": by_bin.get(index, []),
        }
        for index in range(solution.bin_count)
    ]


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    """Parse command-line options."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "-n",
        "--count",
        type=int,
        default=DEFAULT_ITEM_COUNT,
        help="number of random items to pack (default: %(default)s)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=DEFAULT_SEED,
        help="random seed for item generation (default: %(default)s)",
    )
    parser.add_argument(
        "-o",
        "--output",
        type=Path,
        default=Path("packing_result.json"),
        help="file to write the JSON packing result to (default: %(default)s)",
    )
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> None:
    args = parse_args(argv)
    items = make_items(args.count, args.seed)
    solution = solve(items, BIN_CAPACITY, options=SolverOptions(time_limit=60.0))

    records: list[dict[str, object]] = []
    if solution is not None:
        validate(items, BIN_CAPACITY, solution)
        records = to_json(solution, BIN_CAPACITY)

    args.output.write_text(json.dumps(records, indent=2) + "\n", encoding="utf-8")
    print(f"Wrote {len(records)} bins to {args.output}")


if __name__ == "__main__":
    main()
