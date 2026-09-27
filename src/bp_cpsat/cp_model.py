"""Fixed-K CP-SAT model builder for the 3D bin-packing feasibility problem.

Non-overlap is encoded with half-reified Booleans and an enforced
``bool_or``, never with Big-M.

Not yet implemented, tracked as later stages of issue #1 and out of scope here:

* ``Cumulative`` relaxations per axis. Both the interval sizes and the
  cross-sectional demands vary with the chosen orientation, so this wants
  orientation-indexed precomputed values rather than new multiplication
  constraints.
* ``NoOverlap2D`` / ``NoOverlap`` on pairs that preprocessing proved cannot
  separate on one or two axes. Cheap, but it should start from greedy or
  maximal cliques instead of enumerating every maximal clique.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from ortools.sat.python import cp_model

from .models import PackingSolution, Placement
from .preprocess import PairCompatibility, PreparedProblem


@dataclass(frozen=True, slots=True)
class ModelOptions:
    """Internal switches for strengthening constraints, for benchmarking.

    Every field leaves the set of feasible packings unchanged; they only affect
    which constraints are posted and how hard they are to propagate.

    ``symmetry_breaking``
        Force used bin indices to be consecutive from zero (restricted-growth
        numbering). This is a pure symmetry cut and is on by default.
    ``opposite_direction_at_most_one``
        Forbid ``x_ij`` and ``x_ji`` from both holding. They are mutually
        exclusive whenever both items are inside the bin, so this is implied by
        the boundary constraints and costs nothing to keep explicit.
    ``orientation_compatibility``
        Tabulate, per item pair, which orientation combinations may share a
        bin. Prunes assignments the axis literals could not rule out on their
        own, and is on by default.
    ``full_reification``
        Also enforce the converse of each separation literal, pinning literals
        to the truth of their inequalities. **Benchmarked and not recommended:**
        it adds a constraint per axis and direction per pair (36 extra
        constraints on a 4-item, 3-axis instance) and measured consistently
        slower than the default across a 12-instance sweep, slower on 11 of 12
        and never faster. The default half reification leaves the solver free
        to pick whichever separating literal is cheapest, which CP-SAT's
        automatic ``bool_or`` relaxation handles well. Kept switchable so the
        claim stays reproducible.
    """

    symmetry_breaking: bool = True
    opposite_direction_at_most_one: bool = True
    full_reification: bool = False
    orientation_compatibility: bool = True


@dataclass(frozen=True, slots=True)
class Hint:
    """A feasible assignment of one model item, used as a CP-SAT hint."""

    bin_index: int
    orientation: int
    x: int
    y: int
    z: int


@dataclass(frozen=True, slots=True)
class FixedKModel:
    """A feasibility model using exactly ``k`` bin indices."""

    k: int
    model: cp_model.CpModel
    bin_vars: tuple[cp_model.IntVar, ...]
    orientation_vars: tuple[cp_model.IntVar, ...]
    x_vars: tuple[cp_model.IntVar, ...]
    y_vars: tuple[cp_model.IntVar, ...]
    z_vars: tuple[cp_model.IntVar, ...]
    width_vars: tuple[cp_model.IntVar, ...]
    length_vars: tuple[cp_model.IntVar, ...]
    height_vars: tuple[cp_model.IntVar, ...]

    def add_hints(self, hints: Sequence[Hint | None]) -> None:
        """Add optional hints; entries of ``None`` are skipped."""
        for index, hint in enumerate(hints):
            if hint is None:
                continue
            if not 0 <= hint.bin_index < self.k:
                continue
            self.model.add_hint(self.bin_vars[index], hint.bin_index)
            self.model.add_hint(self.orientation_vars[index], hint.orientation)
            self.model.add_hint(self.x_vars[index], hint.x)
            self.model.add_hint(self.y_vars[index], hint.y)
            self.model.add_hint(self.z_vars[index], hint.z)

    def extract(self, solver: cp_model.CpSolver, problem: PreparedProblem) -> PackingSolution:
        """Read the incumbent out of ``solver`` and turn it into a solution."""
        placements: list[Placement] = []
        for index, prepared in enumerate(problem.items):
            placements.append(
                Placement(
                    item_id=prepared.id,
                    bin_index=solver.value(self.bin_vars[index]),
                    x=solver.value(self.x_vars[index]),
                    y=solver.value(self.y_vars[index]),
                    z=solver.value(self.z_vars[index]),
                    width=solver.value(self.width_vars[index]),
                    length=solver.value(self.length_vars[index]),
                    height=solver.value(self.height_vars[index]),
                )
            )
        used = {placement.bin_index for placement in placements}
        bin_count = max(used) + 1 if used else 0
        return PackingSolution(bin_count=bin_count, placements=tuple(placements))


def _add_separation(
    model: cp_model.CpModel,
    options: ModelOptions,
    name: str,
    position_i: cp_model.IntVar,
    size_i: cp_model.IntVar,
    position_j: cp_model.IntVar,
    size_j: cp_model.IntVar,
) -> tuple[cp_model.IntVar, cp_model.IntVar]:
    """Create the two separation literals for one axis of the pair ``i``, ``j``."""
    before = model.new_bool_var(f"{name}_ij")
    after = model.new_bool_var(f"{name}_ji")
    model.add(position_i + size_i <= position_j).only_enforce_if(before)
    model.add(position_j + size_j <= position_i).only_enforce_if(after)
    if options.full_reification:
        model.add(position_i + size_i > position_j).only_enforce_if(before.negated())
        model.add(position_j + size_j > position_i).only_enforce_if(after.negated())
    if options.opposite_direction_at_most_one:
        model.add_at_most_one(before, after)
    return before, after


def _orientation_table(
    problem: PreparedProblem,
    index_i: int,
    index_j: int,
    compatibility: PairCompatibility,
) -> list[tuple[int, int, int]] | None:
    """Tuples ``(same_bin, ori_i, ori_j)`` allowed for the pair, if restricted."""
    count_i = len(problem.items[index_i].orientations)
    count_j = len(problem.items[index_j].orientations)
    allowed: list[tuple[int, int, int]] = []
    forbidden = 0
    for p in range(count_i):
        for q in range(count_j):
            allowed.append((0, p, q))
            if compatibility.allowed[p][q]:
                allowed.append((1, p, q))
            else:
                forbidden += 1
    if forbidden == 0:
        return None
    return allowed


def build_fixed_k_model(problem: PreparedProblem, k: int, options: ModelOptions) -> FixedKModel:
    """Build the fixed-``k`` feasibility model (no objective, no Big-M)."""
    if k < 1 and problem.item_count > 0:
        msg = f"k must be at least 1 when items exist, got {k}"
        raise ValueError(msg)

    bin_capacity = problem.bin_capacity
    model = cp_model.CpModel()
    count = problem.item_count

    bin_vars: list[cp_model.IntVar] = []
    orientation_vars: list[cp_model.IntVar] = []
    x_vars: list[cp_model.IntVar] = []
    y_vars: list[cp_model.IntVar] = []
    z_vars: list[cp_model.IntVar] = []
    width_vars: list[cp_model.IntVar] = []
    length_vars: list[cp_model.IntVar] = []
    height_vars: list[cp_model.IntVar] = []

    for index, prepared in enumerate(problem.items):
        orientations = prepared.orientations
        bin_var = model.new_int_var(0, max(k - 1, 0), f"bin_{index}")
        orientation_var = model.new_int_var(0, len(orientations) - 1, f"ori_{index}")
        width_var = model.new_int_var(
            min(o.width for o in orientations),
            max(o.width for o in orientations),
            f"dx_{index}",
        )
        length_var = model.new_int_var(
            min(o.length for o in orientations),
            max(o.length for o in orientations),
            f"dy_{index}",
        )
        height_var = model.new_int_var(
            min(o.height for o in orientations),
            max(o.height for o in orientations),
            f"dz_{index}",
        )
        x_var = model.new_int_var(0, bin_capacity.width - prepared.min_width, f"x_{index}")
        y_var = model.new_int_var(0, bin_capacity.length - prepared.min_length, f"y_{index}")
        z_var = model.new_int_var(0, bin_capacity.height - prepared.min_height, f"z_{index}")

        model.add_allowed_assignments(
            [orientation_var, width_var, length_var, height_var],
            [
                (position, *orientation.as_tuple())
                for position, orientation in enumerate(orientations)
            ],
        )
        model.add(x_var + width_var <= bin_capacity.width)
        model.add(y_var + length_var <= bin_capacity.length)
        model.add(z_var + height_var <= bin_capacity.height)

        bin_vars.append(bin_var)
        orientation_vars.append(orientation_var)
        x_vars.append(x_var)
        y_vars.append(y_var)
        z_vars.append(z_var)
        width_vars.append(width_var)
        length_vars.append(length_var)
        height_vars.append(height_var)

    if options.symmetry_breaking and count > 0:
        model.add(bin_vars[0] == 0)
        for index in range(1, count):
            running_max = model.new_int_var(0, max(k - 1, 0), f"max_bin_{index}")
            model.add_max_equality(running_max, bin_vars[:index])
            model.add(bin_vars[index] <= running_max + 1)

    for i in range(count):
        for j in range(i + 1, count):
            compatibility = problem.pair(i, j)
            if not compatibility.coexistence_possible:
                model.add(bin_vars[i] != bin_vars[j])
                continue

            same_bin = model.new_bool_var(f"same_{i}_{j}")
            model.add(bin_vars[i] == bin_vars[j]).only_enforce_if(same_bin)
            model.add(bin_vars[i] != bin_vars[j]).only_enforce_if(same_bin.negated())

            separation: list[cp_model.IntVar] = []
            if compatibility.separable[0]:
                separation.extend(
                    _add_separation(
                        model,
                        options,
                        f"x_{i}_{j}",
                        x_vars[i],
                        width_vars[i],
                        x_vars[j],
                        width_vars[j],
                    )
                )
            if compatibility.separable[1]:
                separation.extend(
                    _add_separation(
                        model,
                        options,
                        f"y_{i}_{j}",
                        y_vars[i],
                        length_vars[i],
                        y_vars[j],
                        length_vars[j],
                    )
                )
            if compatibility.separable[2]:
                separation.extend(
                    _add_separation(
                        model,
                        options,
                        f"z_{i}_{j}",
                        z_vars[i],
                        height_vars[i],
                        z_vars[j],
                        height_vars[j],
                    )
                )
            if not separation:  # pragma: no cover - guarded by coexistence_possible
                model.add(bin_vars[i] != bin_vars[j])
                continue

            literals: list[cp_model.LiteralT] = [same_bin.negated(), *separation]
            model.add_bool_or(literals)

            if options.orientation_compatibility:
                table = _orientation_table(problem, i, j, compatibility)
                if table is not None:
                    model.add_allowed_assignments(
                        [same_bin, orientation_vars[i], orientation_vars[j]], table
                    )

    return FixedKModel(
        k=k,
        model=model,
        bin_vars=tuple(bin_vars),
        orientation_vars=tuple(orientation_vars),
        x_vars=tuple(x_vars),
        y_vars=tuple(y_vars),
        z_vars=tuple(z_vars),
        width_vars=tuple(width_vars),
        length_vars=tuple(length_vars),
        height_vars=tuple(height_vars),
    )
