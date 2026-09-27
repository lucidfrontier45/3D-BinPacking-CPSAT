"""Constructive greedy packing used for the upper bound and solution hints.

Points are explored bottom-back-left: lowest ``z`` first, then smallest ``y``,
then smallest ``x``.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum

from .models import (
    Bin,
    Coordinate,
    Item,
    Orientation,
    PackingSolution,
    Placement,
    Shape,
    boxes_overlap,
)
from .orientations import allowed_orientations


class ItemOrder(StrEnum):
    """Deterministic item orderings for the greedy heuristic."""

    VOLUME = "volume"
    MAX_DIMENSION = "max_dimension"
    BASE_AREA = "base_area"


def _sorted_items(items: Sequence[Item], order: ItemOrder) -> list[Item]:
    if order is ItemOrder.MAX_DIMENSION:
        return sorted(items, key=lambda item: (-item.max_dimension, -item.volume, item.id))
    if order is ItemOrder.BASE_AREA:
        return sorted(items, key=lambda item: (-item.base_area, -item.volume, item.id))
    return sorted(items, key=lambda item: (-item.volume, item.id))


def _overlaps(placements: Sequence[Placement], origin: Coordinate, shape: Shape) -> bool:
    return any(
        boxes_overlap(origin, shape, placement.origin, placement.shape) for placement in placements
    )


def _first_position(
    bin_capacity: Bin,
    placements: Sequence[Placement],
    points: Iterable[Coordinate],
    orientations: Sequence[Orientation],
) -> tuple[Coordinate, Orientation] | None:
    """Bottom-back-left first fit over candidate points and orientations.

    Points are tried in ``(z, y, x)`` order, i.e. lowest stack first, then
    nearest the back wall, then nearest the left wall.
    """
    for point in sorted(points, key=lambda candidate: (candidate.z, candidate.y, candidate.x)):
        for orientation in orientations:
            if not point.fits_box(orientation, bin_capacity):
                continue
            if _overlaps(placements, point, orientation):
                continue
            return (point, orientation)
    return None


def _extend_points(
    bin_capacity: Bin, points: set[Coordinate], point: Coordinate, shape: Shape
) -> None:
    for candidate in (
        point.offset(shape.width, 0, 0),
        point.offset(0, shape.length, 0),
        point.offset(0, 0, shape.height),
    ):
        if candidate.lies_within(bin_capacity):
            points.add(candidate)


def greedy_pack(
    items: Sequence[Item],
    bin_capacity: Bin,
    *,
    order: ItemOrder = ItemOrder.VOLUME,
    max_bins: int | None = None,
) -> PackingSolution | None:
    """Pack items with a bottom-back-left first-fit heuristic.

    Returns ``None`` when the packing would need more than ``max_bins`` bins.
    """
    if not items:
        return PackingSolution(bin_count=0, placements=(), optimal=True)

    bin_points: list[set[Coordinate]] = []
    bin_placements: list[list[Placement]] = []

    for item in _sorted_items(items, order):
        orientations = allowed_orientations(item, bin_capacity)
        if not orientations:
            return None
        found: tuple[int, Coordinate, Orientation] | None = None
        for index, placements in enumerate(bin_placements):
            position = _first_position(bin_capacity, placements, bin_points[index], orientations)
            if position is not None:
                found = (index, *position)
                break
        if found is None:
            if max_bins is not None and len(bin_placements) >= max_bins:
                return None
            index = len(bin_placements)
            bin_points.append({Coordinate(0, 0, 0)})
            bin_placements.append([])
            position = _first_position(bin_capacity, [], bin_points[index], orientations)
            if position is None:  # pragma: no cover - orientations are pre-filtered
                return None
            found = (index, *position)

        index, origin, orientation = found
        bin_placements[index].append(
            Placement(
                item_id=item.id,
                bin_index=index,
                origin=origin,
                shape=orientation,
            )
        )
        _extend_points(bin_capacity, bin_points[index], origin, orientation)

    placements = tuple(placement for group in bin_placements for placement in group)
    return PackingSolution(bin_count=len(bin_placements), placements=placements, optimal=False)


def best_greedy_pack(items: Sequence[Item], bin_capacity: Bin) -> PackingSolution | None:
    """Run every ordering and keep the packing with the fewest bins."""
    best: PackingSolution | None = None
    for order in ItemOrder:
        candidate = greedy_pack(items, bin_capacity, order=order)
        if candidate is None:
            continue
        if best is None or candidate.bin_count < best.bin_count:
            best = candidate
    return best
