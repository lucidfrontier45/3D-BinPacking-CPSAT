"""Tests pinning the coexistence_possible / separability invariant (issue #8)."""

import itertools
import random

from bp_cpsat import Bin, Item, PreparedProblem, RotationType, Shape, best_greedy_pack, prepare

BIN = Bin(10, 10, 10)

def _prepared(items: list[Item], bin_capacity: Bin = BIN) -> PreparedProblem:
    greedy = best_greedy_pack(items, bin_capacity)
    assert greedy is not None
    return prepare(items, bin_capacity, greedy)

def test_coexistence_possible_matches_axis_separability() -> None:
    """Pin the coexistence_possible / separability invariant (issue #8).
    ``PairCompatibility.coexistence_possible`` is derived from the per-axis
    separability of the items' minimum extents. It must agree with "some
    orientation pair fits side by side", the fact the Cumulative and
    NoOverlap2D strengthening work in issue #1 will rely on.
    """
    rng = random.Random(0)
    dimensions = (2, 3, 4, 5, 6, 8)
    rotation_policies = (RotationType.NONE, RotationType.FIXED_BOTTOM, RotationType.ALL)
    items = [
        Item(
            f"i{k}",
            Shape(rng.choice(dimensions), rng.choice(dimensions), rng.choice(dimensions)),
            rotation_policies[k % len(rotation_policies)],
        )
        for k in range(12)
    ]
    prepared = _prepared(items)
    for first_index, second_index in itertools.combinations(range(len(prepared.items)), 2):
        first = prepared.items[first_index]
        second = prepared.items[second_index]
        compatibility = prepared.pair(first_index, second_index)
        expected = any(
            first_o.fits_beside(second_o, BIN)
            for first_o in first.orientations
            for second_o in second.orientations
        )
        assert compatibility.coexistence_possible == expected
