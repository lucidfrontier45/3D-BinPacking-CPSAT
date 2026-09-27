"""End-to-end tests: feasibility, rotation policies and minimum bin count."""

import itertools
from random import Random

import pytest
from ortools.sat.python import cp_model

from bp_cpsat import solver as solver_module

from bp_cpsat import (
    Bin,
    Item,
    ModelOptions,
    PackingSolution,
    PreparedProblem,
    RotationType,
    Shape,
    SolverOptions,
    best_greedy_pack,
    build_fixed_k_model,
    build_hints,
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


def _positions(items: list[Item], bin_capacity: Bin = BIN) -> dict[str, tuple[int, int, int]]:
    solution = _solution(items, bin_capacity)
    assert solution is not None
    return {placement.item_id: placement.origin.as_tuple() for placement in solution.placements}


def _bin_count(items: list[Item], bin_capacity: Bin = BIN) -> int | None:
    solution = _solution(items, bin_capacity)
    return None if solution is None else solution.bin_count


def _problem(items: list[Item], bin_capacity: Bin = BIN) -> PreparedProblem:
    greedy = best_greedy_pack(items, bin_capacity)
    assert greedy is not None
    return prepare(items, bin_capacity, greedy)


def test_single_item_that_fits() -> None:
    items = [Item("a", Shape(4, 5, 6))]
    assert _bin_count(items) == 1


def test_single_item_that_cannot_fit_is_infeasible() -> None:
    items = [Item("big", Shape(12, 8, 5), RotationType.NONE)]
    assert solve(items, BIN, options=FAST) is None


def test_single_item_fits_only_after_rotation() -> None:
    bin_capacity = Bin(10, 6, 10)
    items = [Item("big", Shape(7, 8, 5), RotationType.ALL)]
    assert _bin_count([Item("big", Shape(7, 8, 5), RotationType.NONE)], bin_capacity) is None
    assert _bin_count(items, bin_capacity) == 1


def test_two_items_side_by_side_on_x() -> None:
    items = [Item("a", Shape(6, 10, 10)), Item("b", Shape(4, 10, 10))]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[1:] == second[1:] == (0, 0)
    assert first[0] != second[0]


def test_two_items_side_by_side_on_y() -> None:
    items = [Item("a", Shape(10, 6, 10)), Item("b", Shape(10, 4, 10))]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[0] == second[0] == 0
    assert first[2] == second[2] == 0
    assert first[1] != second[1]


def test_two_items_side_by_side_on_z() -> None:
    items = [Item("a", Shape(10, 10, 6)), Item("b", Shape(10, 10, 4))]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[:2] == second[:2] == (0, 0)
    assert first[2] != second[2]


def test_two_items_that_require_different_bins() -> None:
    items = [Item("a", Shape(6, 6, 6)), Item("b", Shape(6, 6, 6))]
    assert _bin_count(items) == 2


def test_stacking_with_overlapping_projections() -> None:
    items = [Item("a", Shape(8, 8, 4)), Item("b", Shape(8, 8, 4))]
    solution = solve(items, BIN, options=FAST)
    assert solution is not None
    validate(items, BIN, solution)
    assert solution.bin_count == 1
    first, second = solution.placements
    assert first.bin_index == second.bin_index
    assert first.origin.x < second.corner.x and second.origin.x < first.corner.x
    assert first.origin.y < second.corner.y and second.origin.y < first.corner.y
    assert first.corner.z <= second.origin.z or second.corner.z <= first.origin.z


def test_touching_coordinates_do_not_overlap() -> None:
    items = [Item("a", Shape(5, 10, 10)), Item("b", Shape(5, 10, 10))]
    assert _bin_count(items) == 1
    first, second = _positions(items).values()
    assert first[1:] == second[1:] == (0, 0)
    assert sorted(x for x, _, _ in (first, second)) == [0, 5]


def test_rotation_none_needs_two_bins_fixed_bottom_needs_one() -> None:
    base = Item("a", Shape(3, 6, 6), RotationType.NONE)
    none = [base, Item("b", Shape(8, 6, 6), RotationType.NONE)]
    fixed_bottom = [base, Item("b", Shape(8, 6, 6), RotationType.FIXED_BOTTOM)]
    assert _bin_count(none) == 2
    assert _bin_count(fixed_bottom) == 1


def test_rotation_fixed_bottom_needs_two_bins_all_needs_one() -> None:
    base = Item("a", Shape(4, 5, 7), RotationType.NONE)
    fixed_bottom = [base, Item("b", Shape(8, 9, 6), RotationType.FIXED_BOTTOM)]
    everything = [base, Item("b", Shape(8, 9, 6), RotationType.ALL)]
    assert _bin_count(fixed_bottom) == 2
    assert _bin_count(everything) == 1


def test_all_items_fit_in_one_bin() -> None:
    items = [Item(f"i{k}", Shape(4, 4, 4), RotationType.ALL) for k in range(8)]
    assert _bin_count(items) == 1


def test_known_two_bin_instance() -> None:
    items = [Item("a", Shape(6, 6, 6)), Item("b", Shape(6, 6, 6))]
    solution = solve(items, BIN, options=FAST)
    assert solution is not None
    assert solution.bin_count == 2
    assert {placement.bin_index for placement in solution.placements} == {0, 1}


def test_volume_lower_bound_is_tight() -> None:
    items = [Item(f"i{k}", Shape(5, 5, 5)) for k in range(16)]
    problem = _problem(items)
    assert problem.volume_lower_bound == 2
    assert problem.clique_lower_bound == 1
    assert problem.lower_bound == 2
    assert _bin_count(items) == 2


def test_incompatibility_clique_raises_the_lower_bound() -> None:
    items = [Item(f"i{k}", Shape(6, 6, 6)) for k in range(3)]
    problem = _problem(items)
    assert problem.volume_lower_bound == 1
    assert problem.clique_lower_bound == 3
    assert problem.lower_bound == 3
    assert _bin_count(items) == 3


def test_searches_when_bounds_are_not_tight() -> None:
    bin_capacity = Bin(8, 8, 8)
    items = [
        Item("i0", Shape(5, 3, 2), RotationType.ALL),
        Item("i1", Shape(5, 2, 6), RotationType.NONE),
        Item("i2", Shape(7, 5, 3), RotationType.FIXED_BOTTOM),
        Item("i3", Shape(4, 7, 5), RotationType.ALL),
        Item("i4", Shape(3, 7, 7), RotationType.NONE),
    ]
    problem = _problem(items, bin_capacity)
    assert problem.lower_bound == 1
    assert problem.upper_bound == 2
    assert _bin_count(items, bin_capacity) == 2


def test_bin_indices_are_consecutive_from_zero() -> None:
    items = [Item(f"i{k}", Shape(6, 6, 6)) for k in range(3)]
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
    # One worker: CP-SAT then explores a single deterministic search path.
    options = SolverOptions(time_limit=15.0, num_search_workers=1)
    items = [Item(f"i{k}", Shape(3, 4, 5), RotationType.ALL) for k in range(6)]
    first = solve(items, BIN, options=options)
    second = solve(items, BIN, options=options)
    assert first is not None and second is not None
    assert first == second


def test_lower_k_is_proven_infeasible() -> None:
    items = [Item("a", Shape(6, 6, 6)), Item("b", Shape(6, 6, 6))]
    solution = solve(items, BIN, options=FAST)
    assert solution is not None
    assert solution.bin_count == 2

    problem = _problem(items)
    fixed = build_fixed_k_model(problem, 1, ModelOptions())
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    assert solver.solve(fixed.model) == cp_model.INFEASIBLE


def test_fixed_k_model_rejects_zero_bins() -> None:
    items = [Item("a", Shape(4, 4, 4))]
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
        Item("a", Shape(6, 6, 6)),
        Item("b", Shape(6, 6, 6)),
        Item("c", Shape(4, 4, 4)),
        Item("d", Shape(4, 4, 4)),
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


def test_full_reification_adds_exactly_one_constraint_per_separation() -> None:
    """Pin the cost claimed in the ``ModelOptions`` docstring.

    ``full_reification`` posts the converse of every separation literal, so it
    must add exactly ``2 * pairs * separable_axes`` constraints. The docstring
    quotes this number as justification for leaving the flag off.
    """
    items = [Item(f"i{t}", Shape(3 + t, 3, 4), RotationType.ALL) for t in range(4)]
    problem = _problem(items, Bin(10, 10, 10))

    def constraint_count(options: ModelOptions) -> int:
        model = build_fixed_k_model(problem, 2, options).model
        return len(model.Proto().constraints)

    without = constraint_count(ModelOptions(full_reification=False))
    with_flag = constraint_count(ModelOptions(full_reification=True))

    axes = 0
    for i in range(len(items)):
        for j in range(i + 1, len(items)):
            axes += sum(problem.pair(i, j).separable)
    assert with_flag - without == 2 * axes


def test_hints_are_optional() -> None:
    items = [Item(f"i{k}", Shape(5, 5, 5)) for k in range(16)]
    with_hints = solve(items, BIN, options=SolverOptions(time_limit=15.0, use_hints=True))
    without_hints = solve(items, BIN, options=SolverOptions(time_limit=15.0, use_hints=False))
    assert with_hints is not None and without_hints is not None
    assert with_hints.bin_count == without_hints.bin_count == 2


def _hard_instance() -> tuple[list[Item], Bin]:
    """A symmetric instance big enough that a tiny budget cuts the search short."""
    bin_capacity = Bin(13, 11, 9)
    items = [
        Item(
            id=f"j{t}",
            shape=Shape(3 + t % 4, 2 + t % 3, 2 + t % 2),
            rotation=RotationType.ALL,
        )
        for t in range(9)
    ]
    return items, bin_capacity


def test_exhausted_budget_still_returns_a_valid_packing() -> None:
    """A scan that runs out of budget must hand back a usable packing, flagged."""
    items, bin_capacity = _hard_instance()
    solution = solve(items, bin_capacity, options=SolverOptions(time_limit=0.0))
    assert solution is not None
    validate(items, bin_capacity, solution)
    if not solution.optimal:
        # A non-optimal answer is still a real packing, not a fabricated count.
        greedy = best_greedy_pack(items, bin_capacity)
        assert greedy is not None
        assert solution.bin_count == greedy.bin_count


def test_optimal_flag_is_set_when_the_scan_proves_a_minimum() -> None:
    items, bin_capacity = _hard_instance()
    solution = solve(items, bin_capacity, options=FAST)
    assert solution is not None
    validate(items, bin_capacity, solution)
    assert solution.optimal is True


def test_per_k_limit_does_not_leak_into_the_returned_answer() -> None:
    """Tight per-call limits must never promote an unproven count to optimal."""
    items, bin_capacity = _hard_instance()
    generous = solve(items, bin_capacity, options=FAST)
    assert generous is not None
    for per_k in (0.0, 0.01, 0.05):
        limited = solve(
            items,
            bin_capacity,
            options=SolverOptions(time_limit=15.0, per_k_time_limit=per_k),
        )
        assert limited is not None
        validate(items, bin_capacity, limited)
        if limited.optimal:
            # Claiming optimality means the count really is the minimum.
            assert limited.bin_count == generous.bin_count
        else:
            greedy = best_greedy_pack(items, bin_capacity)
            assert greedy is not None
            assert limited.bin_count == greedy.bin_count


def test_zero_budget_still_reports_the_proven_lower_bound_case() -> None:
    """With no budget at all, an instance that needs one bin is still provable."""
    solution = solve([Item("a", Shape(4, 5, 6))], BIN, options=SolverOptions(time_limit=0.0))
    assert solution is None or solution.bin_count == 1


def test_status_comparison_uses_value_equality() -> None:
    """CP-SAT hands back a fresh status object, so ``is`` comparisons fail.

    ``CpSolverStatus`` is not a true singleton enum, which means an identity
    check against ``cp_model.UNKNOWN`` silently never matches. Guard the shape
    of that contract so it cannot regress.
    """
    problem = _problem([Item(f"i{k}", Shape(3, 4, 5)) for k in range(4)])
    fixed = build_fixed_k_model(problem, 1, ModelOptions())
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 0.0
    status = solver.solve(fixed.model)
    assert status == cp_model.UNKNOWN
    assert status is not cp_model.UNKNOWN


def test_unknown_fallback_is_verified(monkeypatch: pytest.MonkeyPatch) -> None:
    validation_calls: list[bool] = []

    class UnknownSolver:
        def solve(self, model: cp_model.CpModel) -> cp_model.CpSolverStatus:
            return cp_model.UNKNOWN

    monkeypatch.setattr(solver_module, "_make_solver", lambda options, time_limit: UnknownSolver())
    monkeypatch.setattr(
        solver_module,
        "validate",
        lambda items, bin_capacity, solution: validation_calls.append(True),
    )
    solution = solve([Item("a", Shape(4, 5, 6))], BIN, options=SolverOptions(time_limit=None))
    assert solution is not None
    assert solution.optimal is False
    assert validation_calls == [True]


def test_infeasible_greedy_upper_bound_is_verified_then_raises(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    validation_calls: list[bool] = []

    class InfeasibleSolver:
        def solve(self, model: cp_model.CpModel) -> cp_model.CpSolverStatus:
            return cp_model.INFEASIBLE

    monkeypatch.setattr(
        solver_module, "_make_solver", lambda options, time_limit: InfeasibleSolver()
    )
    monkeypatch.setattr(
        solver_module,
        "validate",
        lambda items, bin_capacity, solution: validation_calls.append(True),
    )
    with pytest.raises(RuntimeError, match="greedy upper-bound model infeasible"):
        solve([Item("a", Shape(4, 5, 6))], BIN, options=SolverOptions(time_limit=None))
    assert validation_calls == [True]


def test_hints_are_never_partial() -> None:
    """``build_hints`` must return a complete assignment for every item.

    Greedy draws its orientations from ``allowed_orientations``, so every
    placement is always found and its orientation is always in the prepared
    set. That is what makes the ``k == UB`` infeasibility guard sound, and it
    is why nothing downstream has to test for partial hints.
    """
    rng = Random(11)
    for _ in range(60):
        bin_capacity = Bin(
            width=rng.randint(2, 8),
            length=rng.randint(2, 8),
            height=rng.randint(2, 8),
        )
        items = [
            Item(
                id=f"i{t}",
                shape=Shape(
                    rng.randint(1, bin_capacity.width),
                    rng.randint(1, bin_capacity.length),
                    rng.randint(1, bin_capacity.height),
                ),
                rotation=rng.choice(list(RotationType)),
            )
            for t in range(rng.randint(1, 5))
        ]
        greedy = best_greedy_pack(items, bin_capacity)
        if greedy is None:
            continue
        problem = prepare(items, bin_capacity, greedy)
        hints = build_hints(problem)
        assert len(hints) == problem.item_count
        assert all(hint is not None for hint in hints)
        # Restricted-growth numbering, as the symmetry-breaking constraints
        # require: bin_0 == 0 and bin_i <= 1 + max(bin_0 .. bin_{i-1}).
        # The sequence is not sorted, only bounded that way.
        indices = [hint.bin_index for hint in hints if hint is not None]
        assert indices[0] == 0
        for i in range(1, len(indices)):
            assert indices[i] <= max(indices[:i]) + 1


@pytest.mark.parametrize(
    ("time_limit", "per_k_time_limit"),
    [
        (-1.0, None),
        (-0.001, None),
        (None, -1.0),
        (None, -5.0),
        (-1.0, -2.0),
    ],
)
def test_negative_time_limits_are_rejected(
    time_limit: float | None, per_k_time_limit: float | None
) -> None:
    """CP-SAT returns ``MODEL_INVALID`` for a negative budget.

    Without this check ``solve`` surfaced that as a confusing "CP-SAT
    rejected the generated model", which blamed the model rather than the
    caller's argument.
    """
    with pytest.raises(ValueError, match="non-negative"):
        SolverOptions(time_limit=time_limit, per_k_time_limit=per_k_time_limit)


@pytest.mark.parametrize(
    ("time_limit", "per_k_time_limit"),
    [
        (0.0, None),
        (None, None),
        (10.0, 0.0),
        (10.0, None),
        (0.0, 0.0),
    ],
)
def test_zero_and_unbounded_time_limits_are_accepted(
    time_limit: float | None, per_k_time_limit: float | None
) -> None:
    """Zero means 'no budget' and None means 'unbounded'; neither is invalid."""
    options = SolverOptions(time_limit=time_limit, per_k_time_limit=per_k_time_limit)
    items = [Item(f"i{k}", Shape(2, 2, 2)) for k in range(3)]
    solution = solve(items, Bin(5, 5, 5), options=options)
    assert solution is not None
    validate(items, Bin(5, 5, 5), solution)
