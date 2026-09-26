"""Public solve API: minimum-bin search over a fixed-K feasibility model."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass, field

from ortools.sat.python import cp_model

from .cp_model import Hint, ModelOptions, build_fixed_k_model
from .heuristic import best_greedy_pack
from .models import Bin, Item, Orientation, PackingSolution
from .preprocess import InfeasibleInstanceError, PreparedProblem, prepare
from .validate import validate


@dataclass(frozen=True, slots=True)
class SolverOptions:
    """Options for :func:`solve`.

    ``time_limit`` applies to each fixed-K feasibility call.
    """

    time_limit: float | None = 30.0
    num_search_workers: int | None = None
    log_search_progress: bool = False
    use_hints: bool = True
    verify: bool = True
    model: ModelOptions = field(default_factory=ModelOptions)


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
        try:
            orientation = prepared.orientations.index(
                Orientation(placement.width, placement.length, placement.height)
            )
        except ValueError:
            hints.append(None)
            continue
        hints.append(
            Hint(
                bin_index=labels[placement.bin_index],
                orientation=orientation,
                x=placement.x,
                y=placement.y,
                z=placement.z,
            )
        )
    return tuple(hints)


def _make_solver(options: SolverOptions) -> cp_model.CpSolver:
    solver = cp_model.CpSolver()
    if options.time_limit is not None:
        solver.parameters.max_time_in_seconds = options.time_limit
    if options.num_search_workers is not None:
        solver.parameters.num_search_workers = options.num_search_workers
    solver.parameters.log_search_progress = options.log_search_progress
    return solver


def solve(
    items: Sequence[Item],
    bin_capacity: Bin,
    *,
    options: SolverOptions | None = None,
) -> PackingSolution | None:
    """Minimize the number of identical bins needed to pack every ``items``.

    Returns the first proven feasible bin count when scanning ``[LB, UB]``, or
    ``None`` when the instance is infeasible or the time limit is exhausted
    before a packing is found.
    """
    opts = options if options is not None else SolverOptions()
    if not items:
        return PackingSolution(bin_count=0, placements=())

    greedy = best_greedy_pack(items, bin_capacity)
    if greedy is None:
        return None
    try:
        problem = prepare(items, bin_capacity, greedy)
    except InfeasibleInstanceError:
        return None

    hints = build_hints(problem) if opts.use_hints else (None,) * problem.item_count
    solver = _make_solver(opts)

    for k in range(problem.lower_bound, problem.upper_bound + 1):
        fixed = build_fixed_k_model(problem, k, opts.model)
        fixed.add_hints(hints)
        status = solver.solve(fixed.model)
        if status is cp_model.MODEL_INVALID:
            msg = "CP-SAT rejected the generated model"
            raise RuntimeError(msg)
        if status in (cp_model.OPTIMAL, cp_model.FEASIBLE):
            solution = fixed.extract(solver, problem)
            if opts.verify:
                validate(items, bin_capacity, solution)
            return solution
    return None
