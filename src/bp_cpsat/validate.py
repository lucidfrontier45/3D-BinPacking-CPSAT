"""Independent validation of packing solutions.

The checks here re-derive everything from the input data and never look at the
CP-SAT model, so a bug in the model cannot hide behind the model itself.
"""

from __future__ import annotations

from collections.abc import Sequence

from .models import Bin, Item, PackingSolution, RotationType


class ValidationError(ValueError):
    """Raised when a solution violates the problem definition."""


def _rotations_allowed(item: Item) -> frozenset[tuple[int, int, int]]:
    width, length, height = item.width, item.length, item.height
    if item.rotation is RotationType.NONE:
        return frozenset({(width, length, height)})
    if item.rotation is RotationType.FIXED_BOTTOM:
        return frozenset({(width, length, height), (length, width, height)})
    return frozenset(
        {
            (width, length, height),
            (width, height, length),
            (length, width, height),
            (length, height, width),
            (height, width, length),
            (height, length, width),
        }
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
        dims = (placement.width, placement.length, placement.height)
        if dims not in _rotations_allowed(item):
            errors.append(f"item {placement.item_id!r} uses disallowed orientation {dims}")
        if (
            placement.x < 0
            or placement.y < 0
            or placement.z < 0
            or placement.x_end > bin_capacity.width
            or placement.y_end > bin_capacity.length
            or placement.z_end > bin_capacity.height
        ):
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
            if first.bin_index != second.bin_index:
                continue
            overlap = (
                first.x < second.x_end
                and second.x < first.x_end
                and first.y < second.y_end
                and second.y < first.y_end
                and first.z < second.z_end
                and second.z < first.z_end
            )
            if overlap:
                errors.append(f"items {first.item_id!r} and {second.item_id!r} overlap")
    return tuple(errors)


def validate(items: Sequence[Item], bin_capacity: Bin, solution: PackingSolution) -> None:
    """Raise :class:`ValidationError` unless ``solution`` is a valid packing."""
    errors = validation_errors(items, bin_capacity, solution)
    if errors:
        msg = "; ".join(errors)
        raise ValidationError(msg)
