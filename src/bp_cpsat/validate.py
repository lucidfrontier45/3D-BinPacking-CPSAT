"""Independent validation of packing solutions.

The checks here re-derive everything from the input data and never look at the
CP-SAT model, so a bug in the model cannot hide behind the model itself.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import Bin, Item, PackingSolution, RotationType, Shape


class ValidationError(ValueError):
    """Raised when a solution violates the problem definition."""


def _rotations_allowed(item: Item) -> frozenset[Shape]:
    """Shapes the item may take, derived independently of the model code."""
    base = item.shape
    if item.rotation is RotationType.NONE:
        return frozenset({base})
    if item.rotation is RotationType.FIXED_BOTTOM:
        return frozenset({base, Shape(base.length, base.width, base.height)})
    width, length, height = base.as_tuple()
    return frozenset(
        Shape(w, l, h)
        for w, l, h in (
            (width, length, height),
            (width, height, length),
            (length, width, height),
            (length, height, width),
            (height, width, length),
            (height, length, width),
        )
    )


def validation_errors(
    items: Sequence[Item], bin_capacity: Bin, solution: PackingSolution
) -> tuple[str, ...]:
    """Return a tuple of human readable problems; empty when the solution is valid."""
    errors: list[str] = []
    by_id = {item.id: item for item in items}
    if len(by_id) != len(items):
        errors.append("item ids are not unique")
        return tuple(errors)

    seen: dict[str, int] = {}
    for placement in solution.placements:
        item = by_id.get(placement.item_id)
        if item is None:
            errors.append(f"unknown item id {placement.item_id!r}")
            continue
        if placement.item_id in seen:
            errors.append(f"item {placement.item_id!r} appears more than once")
            continue
        seen[placement.item_id] = placement.bin_index

        if placement.bin_index < 0:
            errors.append(f"item {placement.item_id!r} has negative bin index")
        if placement.shape not in _rotations_allowed(item):
            dims = placement.shape.as_tuple()
            errors.append(f"item {placement.item_id!r} uses disallowed orientation {dims}")
        if not placement.fits_in(bin_capacity):
            errors.append(f"item {placement.item_id!r} is outside its bin")

    missing = [item.id for item in items if item.id not in seen]
    if missing:
        errors.append(f"missing items: {sorted(missing)}")

    used_bins = {placement.bin_index for placement in solution.placements}
    expected_count = max(used_bins) + 1 if used_bins else 0
    if solution.bin_count != expected_count:
        used = sorted(used_bins)
        errors.append(f"bin_count {solution.bin_count} does not match used bins {used}")
    if any(index not in used_bins for index in range(expected_count)):
        errors.append(f"bin indices are not consecutive from zero: {sorted(used_bins)}")

    for i, first in enumerate(solution.placements):
        for second in solution.placements[i + 1 :]:
            if first.overlaps(second):
                errors.append(f"items {first.item_id!r} and {second.item_id!r} overlap")
    return tuple(errors)


def validate(items: Sequence[Item], bin_capacity: Bin, solution: PackingSolution) -> None:
    """Raise :class:`ValidationError` unless ``solution`` is a valid packing."""
    errors = validation_errors(items, bin_capacity, solution)
    if errors:
        msg = "; ".join(errors)
        raise ValidationError(msg)
