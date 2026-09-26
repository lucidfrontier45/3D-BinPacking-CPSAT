"""Greedy packing heuristic used for the upper bound and hints."""

from bp_cpsat import (
    Bin,
    Item,
    ItemOrder,
    RotationType,
    best_greedy_pack,
    greedy_pack,
    validate,
)

BIN = Bin(10, 10, 10)


def test_greedy_returns_valid_packing() -> None:
    items = [Item(f"i{k}", 4, 5, 6, RotationType.ALL) for k in range(8)]
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
    solution = greedy_pack([Item("a", 4, 5, 6)], BIN)
    assert solution is not None
    assert solution.optimal is False


def test_best_greedy_solution_does_not_claim_optimality() -> None:
    solution = best_greedy_pack([Item("a", 4, 5, 6)], BIN)
    assert solution is not None
    assert solution.optimal is False


def test_greedy_respects_max_bins() -> None:
    items = [Item("a", 10, 10, 10), Item("b", 10, 10, 10), Item("c", 10, 10, 10)]
    assert greedy_pack(items, BIN, max_bins=3) is not None
    assert greedy_pack(items, BIN, max_bins=2) is None


def test_greedy_returns_none_when_an_item_cannot_fit() -> None:
    items = [Item("big", 12, 8, 5)]
    assert greedy_pack(items, BIN) is None


def test_best_greedy_pack_is_valid_and_deterministic() -> None:
    items = [Item(f"i{k}", 3, 4, 5, RotationType.ALL) for k in range(10)]
    first = best_greedy_pack(items, BIN)
    second = best_greedy_pack(list(reversed(items)), BIN)
    assert first is not None and second is not None
    validate(items, BIN, first)
    validate(items, BIN, second)
    assert first.bin_count == second.bin_count
    assert first.placements == second.placements


def test_best_greedy_pack_is_never_worse_than_single_ordering() -> None:
    items = [Item(f"i{k}", 3, 4, 5, RotationType.ALL) for k in range(10)]
    best = best_greedy_pack(items, BIN)
    assert best is not None
    for order in ItemOrder:
        single = greedy_pack(items, BIN, order=order)
        assert single is not None
        assert single.bin_count >= best.bin_count


def test_stacking_is_allowed() -> None:
    items = [Item("a", 8, 8, 5), Item("b", 8, 8, 5)]
    solution = greedy_pack(items, BIN)
    assert solution is not None
    assert solution.bin_count == 1
    validate(items, BIN, solution)
    low = min(solution.placements, key=lambda placement: placement.z)
    high = max(solution.placements, key=lambda placement: placement.z)
    assert low.z + low.height == high.z
