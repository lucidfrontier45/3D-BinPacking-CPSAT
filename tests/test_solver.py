"""End-to-end tests: feasibility, rotation policies and minimum bin count."""

import itertools

import pytest
from ortools.sat.python import cp_model

from bp_cpsat import (
    Bin,
    Item,
    ModelOptions,
    PackingSolution,
    PreparedProblem,
    RotationType,
    SolverOptions,
    best_greedy_pack,
    build_fixed_k_model,
    prepare,
    solve,
    validate,
)

BIN = Bin(10, 10, 10)
FAST = SolverOptions(time_limit=15.0)


def _solution(items: list[Item], bin_capacity: Bin = BIN) -> PackingSolution | None:
    solution = solve(items, bin_capacity, options=FAST)
    if solution is None:
        return None
    validate(items, bin_capacity, solution)
    return solution


def _positions(
    items: list[Item], bin_capacity: Bin = BIN
) -> dict[str, tuple[int, int, int]]:
    solution = _solution(items, bin_capacity)
    assert solution is not None
    return {
        placement.item_id: (placement.x, placement.y, placement.z)
        for placement in solution.placements
    }


def _bin_count(items: list[Item], bin_capacity: Bin = BIN) -> int | None:
    solution = _solution(items, bin_capacity)
    return None if solution is None else solution.bin_count


def _problem(items: list[Item], bin_capacity: Bin = BIN) -> PreparedProblem:
    greedy = best_greedy_pack(items, bin_capacity)
    assert greedy is not None
    return prepare(items, bin_capacity, greedy)


def test_single_item_that_fits() -> None:
    items = [Item("a", 4, 5, 6)]
    assert _bin_count(items) == 1


def test_single_item_that_cannot_fit_is_infeasible() -> None:
    items = [Item("big", 12, 8, 5, RotationType.NONE)]
    assert solve(items, BIN, options=FAST) is None


def test_single_item_fits_only_after_rotation() -> None:
    bin_capacity = Bin(10, 6, 10)
    items = [Item("big", 7, 8, 5, RotationType.ALL)]
    assert _bin_count([Item("big", 7, 8, 5, RotationType.NONE)], bin_capacity) is None
    assert _bin_count(items, bin_capacity) == 1


def test_two_items_side_by_side_on_x() -> None:
    items = [Item("a", 6, 10, 10), Item("b", 4, 10, 10)]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[1:] == second[1:] == (0, 0)
    assert first[0] != second[0]


def test_two_items_side_by_side_on_y() -> None:
    items = [Item("a", 10, 6, 10), Item("b", 10, 4, 10)]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[0] == second[0] == 0
    assert first[2] == second[2] == 0
    assert first[1] != second[1]


def test_two_items_side_by_side_on_z() -> None:
    items = [Item("a", 10, 10, 6), Item("b", 10, 10, 4)]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[:2] == second[:2] == (0, 0)
    assert first[2] != second[2]


def test_two_items_that_require_different_bins() -> None:
    items = [Item("a", 6, 6, 6), Item("b", 6, 6, 6)]
    assert _bin_count(items) == 2


def test_stacking_with_overlapping_projections() -> None:
    items = [Item("a", 8, 8, 4), Item("b", 8, 8, 4)]
    solution = solve(items, BIN, options=FAST)
    assert solution is not None
    validate(items, BIN, solution)
    assert solution.bin_count == 1
    first, second = solution.placements
    assert first.bin_index == second.bin_index
    assert first.x < second.x_end and second.x < first.x_end
    assert first.y < second.y_end and second.y < first.y_end
    assert first.z_end <= second.z or second.z_end <= first.z


def test_touching_coordinates_do_not_overlap() -> None:
    items = [Item("a", 5, 10, 10), Item("b", 5, 10, 10)]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[1:] == second[1:] == (0, 0)
    assert sorted(x for x, _, _ in (first, second)) == [0, 5]


def test_rotation_none_needs_two_bins_fixed_bottom_needs_one() -> None:
    base = Item("a", 3, 6, 6, RotationType.NONE)
    none = [base, Item("b", 8, 6, 6, RotationType.NONE)]
    fixed_bottom = [base, Item("b", 8, 6, 6, RotationType.FIXED_BOTTOM)]
    assert _bin_count(none) == 2
    assert _bin_count(fixed_bottom) == 1


def test_rotation_fixed_bottom_needs_two_bins_all_needs_one() -> None:
    base = Item("a", 4, 5, 7, RotationType.NONE)
    fixed_bottom = [base, Item("b", 8, 9, 6, RotationType.FIXED_BOTTOM)]
    everything = [base, Item("b", 8, 9, 6, RotationType.ALL)]
    assert _bin_count(fixed_bottom) == 2
    assert _bin_count(everything) == 1


def test_all_items_fit_in_one_bin() -> None:
    items = [Item(f"i{k}", 4, 4, 4, RotationType.ALL) for k in range(8)]
    assert _bin_count(items) == 1


def test_known_two_bin_instance() -> None:
    items = [Item("a", 6, 6, 6), Item("b", 6, 6, 6)]
    solution = solve(items, BIN, options=FAST)
    assert solution is not None
    assert solution.bin_count == 2
    assert {placement.bin_index for placement in solution.placements} == {0, 1}


def test_volume_lower_bound_is_tight() -> None:
    items = [Item(f"i{k}", 5, 5, 5) for k in range(16)]
    problem = _problem(items)
    assert problem.volume_lower_bound == 2
    assert problem.clique_lower_bound == 1
    assert problem.lower_bound == 2
    assert _bin_count(items) == 2


def test_incompatibility_clique_raises_the_lower_bound() -> None:
    items = [Item(f"i{k}", 6, 6, 6) for k in range(3)]
    problem = _problem(items)
    assert problem.volume_lower_bound == 1
    assert problem.clique_lower_bound == 3
    assert problem.lower_bound == 3
    assert _bin_count(items) == 3


def test_searches_when_bounds_are_not_tight() -> None:
    bin_capacity = Bin(8, 8, 8)
    items = [
        Item("i0", 5, 3, 2, RotationType.ALL),
        Item("i1", 5, 2, 6, RotationType.NONE),
        Item("i2", 7, 5, 3, RotationType.FIXED_BOTTOM),
        Item("i3", 4, 7, 5, RotationType.ALL),
        Item("i4", 3, 7, 7, RotationType.NONE),
    ]
    problem = _problem(items, bin_capacity)
    assert problem.lower_bound == 1
    assert problem.upper_bound == 2
    assert _bin_count(items, bin_capacity) == 2


def test_bin_indices_are_consecutive_from_zero() -> None:
    items = [Item(f"i{k}", 6, 6, 6) for k in range(3)]
    solution = solve(items, BIN, options=FAST)
    assert solution is not None
    used = sorted({placement.bin_index for placement in solution.placements})
    assert used == list(range(solution.bin_count))


def test_empty_instance_uses_no_bins() -> None:
    solution = solve([], BIN, options=FAST)
    assert solution is not None
    assert solution.bin_count == 0
    assert solution.placements == ()


def test_deterministic_on_tiny_instance() -> None:
    items = [Item(f"i{k}", 3, 4, 5, RotationType.ALL) for k in range(6)]
    first = solve(items, BIN, options=FAST)
    second = solve(items, BIN, options=FAST)
    assert first == second


def test_lower_k_is_proven_infeasible() -> None:
    items = [Item("a", 6, 6, 6), Item("b", 6, 6, 6)]
    solution = solve(items, BIN, options=FAST)
    assert solution is not None
    assert solution.bin_count == 2

    problem = _problem(items)
    fixed = build_fixed_k_model(problem, 1, ModelOptions())
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    assert solver.solve(fixed.model) == cp_model.INFEASIBLE


def test_fixed_k_model_rejects_zero_bins() -> None:
    items = [Item("a", 4, 4, 4)]
    problem = _problem(items)
    with pytest.raises(ValueError, match="at least 1"):
        build_fixed_k_model(problem, 0, ModelOptions())


@pytest.mark.parametrize(
    (
        "symmetry_breaking",
        "at_most_one",
        "full_reification",
        "orientation_compatibility",
    ),
    list(itertools.product((True, False), repeat=4)),
)
def test_model_options_agree_on_the_optimum(
    symmetry_breaking: bool,
    at_most_one: bool,
    full_reification: bool,
    orientation_compatibility: bool,
) -> None:
    items = [
        Item("a", 6, 6, 6),
        Item("b", 6, 6, 6),
        Item("c", 4, 4, 4),
        Item("d", 4, 4, 4),
    ]
    options = SolverOptions(
        time_limit=15.0,
        use_hints=False,
        model=ModelOptions(
            symmetry_breaking=symmetry_breaking,
            opposite_direction_at_most_one=at_most_one,
            full_reification=full_reification,
            orientation_compatibility=orientation_compatibility,
        ),
    )
    solution = solve(items, BIN, options=options)
    assert solution is not None
    assert solution.bin_count == 2
    validate(items, BIN, solution)


def test_hints_are_optional() -> None:
    items = [Item(f"i{k}", 5, 5, 5) for k in range(16)]
    with_hints = solve(
        items, BIN, options=SolverOptions(time_limit=15.0, use_hints=True)
    )
    without_hints = solve(
        items, BIN, options=SolverOptions(time_limit=15.0, use_hints=False)
    )
    assert with_hints is not None and without_hints is not None
    assert with_hints.bin_count == without_hints.bin_count == 2
