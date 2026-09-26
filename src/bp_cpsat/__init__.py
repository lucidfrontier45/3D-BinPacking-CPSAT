"""3D bin packing on OR-Tools CP-SAT."""

from .cp_model import FixedKModel, Hint, ModelOptions, build_fixed_k_model
from .heuristic import ItemOrder, best_greedy_pack, greedy_pack
from .models import Bin, Item, Orientation, PackingSolution, Placement, RotationType
from .orientations import allowed_orientations, candidate_orientations
from .preprocess import (
    InfeasibleInstanceError,
    PairCompatibility,
    PreparedItem,
    PreparedProblem,
    build_pair_compatibility,
    prepare,
)
from .solver import SolverOptions, build_hints, solve
from .validate import ValidationError, validate, validation_errors
from .version import __version__

__all__ = [
    "Bin",
    "FixedKModel",
    "Hint",
    "InfeasibleInstanceError",
    "Item",
    "ItemOrder",
    "ModelOptions",
    "Orientation",
    "PackingSolution",
    "PairCompatibility",
    "Placement",
    "PreparedItem",
    "PreparedProblem",
    "RotationType",
    "SolverOptions",
    "ValidationError",
    "__version__",
    "allowed_orientations",
    "best_greedy_pack",
    "build_fixed_k_model",
    "build_hints",
    "build_pair_compatibility",
    "candidate_orientations",
    "greedy_pack",
    "prepare",
    "solve",
    "validate",
    "validation_errors",
]
