"""Bounds, pairwise compatibility and incompatibility preprocessing."""

import pytest

from bp_cpsat import (
    Bin,
    InfeasibleInstanceError,
    Item,
    PackingSolution,
    PreparedProblem,
    RotationType,
    best_greedy_pack,
    build_pair_compatibility,
    prepare,
)
from bp_cpsat.preprocess import incompatibility_clique_lower_bound, volume_lower_bound

BIN = Bin(10, 10, 10)


def _prepared(items: list[Item], bin_capacity: Bin = BIN) -> PreparedProblem:
    greedy = best_greedy_pack(items, bin_capacity)
    assert greedy is not None
    return prepare(items, bin_capacity, greedy)


def test_volume_lower_bound_is_ceil_of_total_volume() -> None:
    items = [Item("a", 10, 10, 1), Item("b", 10, 10, 1), Item("c", 10, 10, 1)]
    prepared_items = _prepared(items).items
    assert sum(item.volume for item in prepared_items) == 300
    assert volume_lower_bound(prepared_items, BIN) == 1

    big = [Item("a", 10, 10, 2), Item("b", 10, 10, 2), Item("c", 10, 10, 2)]
    prepared_big = _prepared(big).items
    assert volume_lower_bound(prepared_big, BIN) == 1

    exactly_two = [Item(f"i{k}", 5, 5, 5) for k in range(16)]
    prepared_exact = _prepared(exactly_two).items
    assert volume_lower_bound(prepared_exact, BIN) == 2


def test_incompatible_pair_has_no_separable_axis() -> None:
    prepared = _prepared([Item("a", 6, 6, 6), Item("b", 6, 6, 6)])
    compatibility = prepared.pair(0, 1)
    assert compatibility.separable == (False, False, False)
    assert not compatibility.coexistence_possible
    assert compatibility.allowed == ((False,),)


def test_separable_axis_is_detected_per_axis() -> None:
    prepared = _prepared([Item("a", 6, 6, 6), Item("b", 4, 6, 6)])
    compatibility = prepared.pair(0, 1)
    assert compatibility.separable == (True, False, False)
    assert compatibility.coexistence_possible
    assert compatibility.allowed == ((True,),)


def test_orientation_pair_filtering_uses_selected_orientations() -> None:
    items = [
        Item("a", 4, 5, 7, RotationType.NONE),
        Item("b", 8, 9, 6, RotationType.ALL),
    ]
    prepared = _prepared(items)
    compatibility = prepared.pair(0, 1)
    assert compatibility.separable == (True, False, False)
    allowed = compatibility.allowed
    assert len(allowed) == 6
    assert {len(row) for row in allowed} == {1}
    assert sum(row[0] for row in allowed) == 2
    assert not all(row[0] for row in allowed)


def test_build_pair_compatibility_is_order_independent_for_separability() -> None:
    prepared = _prepared([Item("a", 4, 5, 7), Item("b", 8, 9, 6, RotationType.ALL)])
    forward = build_pair_compatibility(prepared.items[0], prepared.items[1], BIN)
    backward = build_pair_compatibility(prepared.items[1], prepared.items[0], BIN)
    assert forward.separable == backward.separable
    assert forward.coexistence_possible == backward.coexistence_possible


def test_incompatible_clique_lower_bound() -> None:
    items = [Item(f"i{k}", 6, 6, 6) for k in range(3)]
    prepared = _prepared(items)
    assert volume_lower_bound(prepared.items, BIN) == 1
    assert incompatibility_clique_lower_bound(prepared.pairs, len(prepared.items)) == 3
    assert prepared.lower_bound == 3


def test_clique_lower_bound_is_one_when_all_items_fit_together() -> None:
    items = [Item(f"i{k}", 2, 2, 2) for k in range(5)]
    prepared = _prepared(items)
    assert incompatibility_clique_lower_bound(prepared.pairs, len(prepared.items)) == 1


def test_prepare_orders_items_by_decreasing_volume_then_id() -> None:
    items = [Item("small", 2, 2, 2), Item("big", 5, 5, 5), Item("also-big", 5, 5, 5)]
    prepared = _prepared(items)
    assert [item.id for item in prepared.items] == ["also-big", "big", "small"]
    assert prepared.items[0].volume >= prepared.items[1].volume >= prepared.items[2].volume


def test_prepare_records_total_volume_and_bounds() -> None:
    items = [Item(f"i{k}", 6, 6, 6) for k in range(3)]
    prepared = _prepared(items)
    assert prepared.total_volume == 648
    assert prepared.volume_lower_bound == 1
    assert prepared.clique_lower_bound == 3
    assert prepared.lower_bound == 3
    assert prepared.upper_bound >= prepared.lower_bound


def test_prepare_raises_when_an_item_cannot_fit() -> None:
    stub = PackingSolution(bin_count=0, placements=())
    with pytest.raises(InfeasibleInstanceError, match="does not fit"):
        prepare([Item("big", 12, 8, 5)], BIN, stub)


def test_prepare_rejects_duplicate_ids() -> None:
    with pytest.raises(ValueError, match="unique"):
        _prepared([Item("same", 2, 2, 2), Item("same", 3, 3, 3)])
