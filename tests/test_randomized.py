"""Randomized small instances checked against the independent validator."""

import random

import pytest
from ortools.sat.python import cp_model

from bp_cpsat import (
    Bin,
    Item,
    ModelOptions,
    RotationType,
    SolverOptions,
    best_greedy_pack,
    build_fixed_k_model,
    prepare,
    solve,
    validate,
)

SEED = 20260926
FAST = SolverOptions(time_limit=15.0)


def _instance(trial: int) -> tuple[list[Item], Bin]:
    rng = random.Random(SEED + trial)
    side = rng.randint(5, 10)
    bin_capacity = Bin(side, side, side)
    count = rng.randint(1, 10)
    items = [
        Item(
            f"i{k}",
            rng.randint(1, side),
            rng.randint(1, side),
            rng.randint(1, side),
            rng.choice(list(RotationType)),
        )
        for k in range(count)
    ]
    return items, bin_capacity


def _bounds(items: list[Item], bin_capacity: Bin) -> tuple[int, int]:
    greedy = best_greedy_pack(items, bin_capacity)
    assert greedy is not None
    problem = prepare(items, bin_capacity, greedy)
    return problem.lower_bound, problem.upper_bound


@pytest.mark.parametrize("trial", range(15))
def test_random_instance_solution_is_valid(trial: int) -> None:
    items, bin_capacity = _instance(trial)
    solution = solve(items, bin_capacity, options=FAST)
    assert solution is not None
    validate(items, bin_capacity, solution)
    lower, upper = _bounds(items, bin_capacity)
    assert lower <= solution.bin_count <= upper


@pytest.mark.parametrize("trial", range(5))
def test_random_instance_is_deterministic_with_one_worker(trial: int) -> None:
    items, bin_capacity = _instance(trial)
    options = SolverOptions(time_limit=15.0, num_search_workers=1)
    first = solve(items, bin_capacity, options=options)
    second = solve(items, bin_capacity, options=options)
    assert first is not None and second is not None
    assert first == second


@pytest.mark.parametrize("trial", range(5))
def test_random_instance_bin_count_is_stable_under_parallel_search(trial: int) -> None:
    items, bin_capacity = _instance(trial)
    counts = set()
    for _ in range(3):
        solution = solve(items, bin_capacity, options=FAST)
        assert solution is not None
        validate(items, bin_capacity, solution)
        counts.add(solution.bin_count)
    assert len(counts) == 1


@pytest.mark.parametrize("trial", range(15))
def test_random_instance_respects_tight_independent_bounds(trial: int) -> None:
    items, bin_capacity = _instance(trial)
    lower, upper = _bounds(items, bin_capacity)
    if lower != upper:
        pytest.skip("bounds are not tight for this instance")
    solution = solve(items, bin_capacity, options=FAST)
    assert solution is not None
    assert solution.bin_count == lower


@pytest.mark.parametrize("trial", range(3))
def test_random_instance_smaller_k_is_proven_infeasible(trial: int) -> None:
    items, bin_capacity = _instance(trial)
    solution = solve(items, bin_capacity, options=FAST)
    assert solution is not None
    greedy = best_greedy_pack(items, bin_capacity)
    assert greedy is not None
    problem = prepare(items, bin_capacity, greedy)
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15.0
    for k in range(problem.lower_bound, solution.bin_count):
        fixed = build_fixed_k_model(problem, k, ModelOptions())
        assert solver.solve(fixed.model) == cp_model.INFEASIBLE
