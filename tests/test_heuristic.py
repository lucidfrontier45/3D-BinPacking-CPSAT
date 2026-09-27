"""Greedy packing heuristic used for the upper bound and hints."""

from typing import cast

import pytest

from bp_cpsat import (
    Bin,
    Item,
    ItemOrder,
    Shape,
    RotationType,
    best_greedy_pack,
    greedy_pack,
    validate,
)

BIN = Bin(10, 10, 10)


def test_greedy_returns_valid_packing() -> None:
    items = [Item(f"i{k}", Shape(4, 5, 6), RotationType.ALL) for k in range(8)]
    solution = greedy_pack(items, BIN)
    assert solution is not None
    validate(items, BIN, solution)


def test_greedy_handles_empty_instance() -> None:
    solution = greedy_pack([], BIN)
    assert solution is not None
    assert solution.bin_count == 0
    assert solution.placements == ()
    assert solution.optimal is True


def test_non_empty_greedy_solution_does_not_claim_optimality() -> None:
    solution = greedy_pack([Item("a", Shape(4, 5, 6))], BIN)
    assert solution is not None
    assert solution.optimal is False


def test_best_greedy_solution_does_not_claim_optimality() -> None:
    solution = best_greedy_pack([Item("a", Shape(4, 5, 6))], BIN)
    assert solution is not None
    assert solution.optimal is False


def test_greedy_respects_max_bins() -> None:
    items = [
        Item("a", Shape(10, 10, 10)),
        Item("b", Shape(10, 10, 10)),
        Item("c", Shape(10, 10, 10)),
    ]
    assert greedy_pack(items, BIN, max_bins=3) is not None
    assert greedy_pack(items, BIN, max_bins=2) is None


def test_greedy_returns_none_when_an_item_cannot_fit() -> None:
    items = [Item("big", Shape(12, 8, 5))]
    assert greedy_pack(items, BIN) is None


def test_best_greedy_pack_is_valid_and_deterministic() -> None:
    items = [Item(f"i{k}", Shape(3, 4, 5), RotationType.ALL) for k in range(10)]
    first = best_greedy_pack(items, BIN)
    second = best_greedy_pack(list(reversed(items)), BIN)
    assert first is not None and second is not None
    validate(items, BIN, first)
    validate(items, BIN, second)
    assert first.bin_count == second.bin_count
    assert first.placements == second.placements


def test_best_greedy_pack_is_never_worse_than_single_ordering() -> None:
    items = [Item(f"i{k}", Shape(3, 4, 5), RotationType.ALL) for k in range(10)]
    best = best_greedy_pack(items, BIN)
    assert best is not None
    for order in ItemOrder:
        single = greedy_pack(items, BIN, order=order)
        assert single is not None
        assert single.bin_count >= best.bin_count


def test_stacking_is_allowed() -> None:
    items = [Item("a", Shape(8, 8, 5)), Item("b", Shape(8, 8, 5))]
    solution = greedy_pack(items, BIN)
    assert solution is not None
    assert solution.bin_count == 1
    validate(items, BIN, solution)
    low = min(solution.placements, key=lambda placement: placement.origin.z)
    high = max(solution.placements, key=lambda placement: placement.origin.z)
    assert low.origin.z + low.shape.height == high.origin.z


# Shapes chosen so the orderings genuinely disagree: ``base_area`` needs two
# bins where ``volume`` needs one, so parity cannot hold by coincidence.
DISCRIMINATING_ITEMS = [
    Item(f"i{k}", Shape(w, l, h), RotationType.ALL)
    for k, (w, l, h) in enumerate(
        [(1, 2, 1), (1, 2, 7), (1, 2, 7), (1, 3, 3), (1, 2, 2), (3, 2, 4)]
    )
]
DISCRIMINATING_BIN = Bin(3, 4, 7)


def test_the_orderings_actually_differ_on_the_discriminating_instance() -> None:
    """Guard the fixture: the parity test below is only meaningful if the
    orderings produce different packings to begin with."""
    counts = set()
    for order in ItemOrder:
        solution = greedy_pack(DISCRIMINATING_ITEMS, DISCRIMINATING_BIN, order=order)
        assert solution is not None
        counts.add(solution.bin_count)
    assert len(counts) > 1


@pytest.mark.parametrize("order", list(ItemOrder))
def test_string_order_matches_enum_member(order: ItemOrder) -> None:
    """``ItemOrder`` is a ``StrEnum``, so ``order is ItemOrder.BASE_AREA`` misses
    a plain string that is value-equal to the member, silently degrading to the
    ``VOLUME`` default instead of raising."""
    as_member = greedy_pack(DISCRIMINATING_ITEMS, DISCRIMINATING_BIN, order=order)
    as_string = greedy_pack(
        DISCRIMINATING_ITEMS, DISCRIMINATING_BIN, order=cast(ItemOrder, str(order))
    )
    assert as_member is not None
    assert as_string is not None
    assert as_string == as_member


def test_unknown_order_string_is_rejected() -> None:
    with pytest.raises(ValueError):
        greedy_pack(DISCRIMINATING_ITEMS, DISCRIMINATING_BIN, order=cast(ItemOrder, "nope"))
