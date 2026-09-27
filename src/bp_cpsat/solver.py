"""Public solve API: minimum-bin search over a fixed-K feasibility model."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field
from time import perf_counter

from ortools.sat.python import cp_model

from .cp_model import Hint, ModelOptions, build_fixed_k_model
from .heuristic import best_greedy_pack
from .models import Bin, Item, PackingSolution
from .preprocess import InfeasibleInstanceError, PreparedProblem, prepare
from .validate import validate


@dataclass(frozen=True, slots=True)
class SolverOptions:
    """Options for :func:`solve`.

    ``time_limit`` bounds the *whole* ``[LB, UB]`` search, not each fixed-K call
    on its own, so the total runtime does not grow with the width of the range.
    ``per_k_time_limit`` narrows the slice given to each individual feasibility
    call within that overall budget; leave it ``None`` to let the solver use the
    remaining budget for every call.
    """

    time_limit: float | None = 30.0
    num_search_workers: int | None = None
    log_search_progress: bool = False
    use_hints: bool = True
    verify: bool = True
    model: ModelOptions = field(default_factory=ModelOptions)
    per_k_time_limit: float | None = None

    def __post_init__(self) -> None:
        for name in ("time_limit", "per_k_time_limit"):
            value = getattr(self, name)
            if value is not None and value < 0:
                msg = f"{name} must be non-negative or None, got {value}"
                raise ValueError(msg)


def build_hints(problem: PreparedProblem) -> tuple[Hint | None, ...]:
    """Turn the greedy packing into per-item hints in canonical item order.

    Bin indices are relabelled in order of first appearance so the hints are
    consistent with the restricted-growth symmetry breaking.
    """
    by_id = {placement.item_id: placement for placement in problem.greedy_placements}
    labels: dict[int, int] = {}
    hints: list[Hint | None] = []
    for prepared in problem.items:
        placement = by_id.get(prepared.id)
        if placement is None:
            hints.append(None)
            continue
        if placement.bin_index not in labels:
            labels[placement.bin_index] = len(labels)
        orientation = next(
            (
                index
                for index, candidate in enumerate(prepared.orientations)
                if candidate == placement.shape
            ),
            None,
        )
        if orientation is None:
            hints.append(None)
            continue
        hints.append(
            Hint(
                bin_index=labels[placement.bin_index],
                orientation=orientation,
                origin=placement.origin,
            )
        )
    return tuple(hints)


def _make_solver(options: SolverOptions, time_limit: float | None) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    if time_limit is not None:
        solver.parameters.max_time_in_seconds = time_limit
    if options.num_search_workers is not None:
        solver.parameters.num_search_workers = options.num_search_workers
    solver.parameters.log_search_progress = options.log_search_progress
    return solver


def _with_optimality(solution: PackingSolution, optimal: bool) -> PackingSolution:
    if solution.optimal == optimal:
        return solution
    return PackingSolution(
        bin_count=solution.bin_count,
        placements=solution.placements,
        optimal=optimal,
    )


def solve(
    items: Sequence[Item],
    bin_capacity: Bin,
    *,
    options: SolverOptions | None = None,
) -> PackingSolution | None:
    """Minimize the number of identical bins needed to pack every ``items``.

    Scans ``K`` from the lower bound up to the greedy upper bound and stops at
    the first ``K`` that is proven feasible. Feasibility is monotone in the
    number of identical bins, so that ``K`` is the proven minimum whenever the
    scan reaches it. Concretely, the symmetry-breaking constraints force the
    used indices to be ``{0..m-1}`` for some ``m <= K``; if ``m < K`` the same
    placements relabelled into ``m`` bins would already have made the ``m``-bin
    model feasible, contradicting the fact that the scan has not stopped yet.
    The reported ``bin_count`` therefore always equals the scanned ``K``.

    Returns ``None`` only when the instance is *proven* infeasible: some ``K``
    in the scanned range was proven infeasible, or a greedy packing could not
    place an item at all. A scan that runs out of its time budget before
    ruling out a smaller bin count still returns the best packing found, with
    ``PackingSolution.optimal`` set to ``False``.
    """
    opts = options if options is not None else SolverOptions()
    if not items:
        return PackingSolution(bin_count=0, placements=(), optimal=True)

    greedy = best_greedy_pack(items, bin_capacity)
    if greedy is None:
        return None
    try:
        problem = prepare(items, bin_capacity, greedy)
    except InfeasibleInstanceError:
        return None

    hints = build_hints(problem) if opts.use_hints else (None,) * problem.item_count
    deadline = None if opts.time_limit is None else perf_counter() + opts.time_limit
    exhausted = False

    for k in range(problem.lower_bound, problem.upper_bound + 1):
        remaining = None if deadline is None else deadline - perf_counter()
        if remaining is not None and remaining <= 0:
            exhausted = True
            break
        time_limit = remaining
        if opts.per_k_time_limit is not None:
            time_limit = (
                opts.per_k_time_limit
                if time_limit is None
                else min(time_limit, opts.per_k_time_limit)
            )
        solver = _make_solver(opts, time_limit)
        fixed = build_fixed_k_model(problem, k, opts.model)
        fixed.add_hints(hints)
        status = solver.solve(fixed.model)
        if status == cp_model.MODEL_INVALID:
            msg = "CP-SAT rejected the generated model"
            raise RuntimeError(msg)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solution = fixed.extract(solver, problem)
            if opts.verify:
                validate(items, bin_capacity, solution)
            return _with_optimality(solution, optimal=True)
        if status == cp_model.UNKNOWN:
            # This ``K`` is neither feasible nor refuted, so no smaller bin
            # count has been ruled out. Anything found from here on would be an
            # upper bound only, so stop and hand back the best packing we have.
            if opts.verify:
                validate(items, bin_capacity, greedy)
            return _with_optimality(greedy, optimal=False)
        if status == cp_model.INFEASIBLE and k == problem.upper_bound:
            # The greedy packing already assigned every item to at most ``UB``
            # bins, so the ``UB``-bin model is feasible by construction. A
            # proven infeasibility here contradicts that invariant and points
            # to a model/heuristic inconsistency; validate the incumbent before
            # surfacing the contradiction.
            if opts.verify:
                validate(items, bin_capacity, greedy)
            msg = "CP-SAT proved the greedy upper-bound model infeasible"
            raise RuntimeError(msg)
    if exhausted:
        if opts.verify:
            validate(items, bin_capacity, greedy)
        return _with_optimality(greedy, optimal=False)
    # Every remaining ``K`` was proven infeasible, so the instance is.
    return None
