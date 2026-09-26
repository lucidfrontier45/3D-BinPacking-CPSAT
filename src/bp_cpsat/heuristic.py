"""Constructive greedy packing used for the upper bound and solution hints."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from enum import StrEnum

from .models import Bin, Item, Orientation, PackingSolution, Placement
from .orientations import allowed_orientations

Point = tuple[int, int, int]


class ItemOrder(StrEnum):
    """Deterministic item orderings for the greedy heuristic."""

    VOLUME = "volume"
    MAX_DIMENSION = "max_dimension"
    BASE_AREA = "base_area"


def _sorted_items(items: Sequence[Item], order: ItemOrder) -> list[Item]:
    if order is ItemOrder.MAX_DIMENSION:
        return sorted(
            items, key=lambda item: (-item.max_dimension, -item.volume, item.id)
        )
    if order is ItemOrder.BASE_AREA:
        return sorted(items, key=lambda item: (-item.base_area, -item.volume, item.id))
    return sorted(items, key=lambda item: (-item.volume, item.id))


def _overlaps(
    placements: Sequence[Placement], x: int, y: int, z: int, orientation: Orientation
) -> bool:
    x_end = x + orientation.width
    y_end = y + orientation.length
    z_end = z + orientation.height
    return any(
        x < placement.x_end
        and placement.x < x_end
        and y < placement.y_end
        and placement.y < y_end
        and z < placement.z_end
        and placement.z < z_end
        for placement in placements
    )


def _first_position(
    bin_capacity: Bin,
    placements: Sequence[Placement],
    points: Iterable[Point],
    orientations: Sequence[Orientation],
) -> tuple[Point, Orientation] | None:
    """Bottom-left-back first fit over candidate points and orientations."""
    for x, y, z in sorted(points, key=lambda point: (point[2], point[1], point[0])):
        if x >= bin_capacity.width:
            continue
        if y >= bin_capacity.length or z >= bin_capacity.height:
            continue
        for orientation in orientations:
            if x + orientation.width > bin_capacity.width:
                continue
            if y + orientation.length > bin_capacity.length:
                continue
            if z + orientation.height > bin_capacity.height:
                continue
            if _overlaps(placements, x, y, z, orientation):
                continue
            return (x, y, z), orientation
    return None


def _extend_points(
    bin_capacity: Bin, points: set[Point], point: Point, orientation: Orientation
) -> None:
    x, y, z = point
    for candidate in (
        (x + orientation.width, y, z),
        (x, y + orientation.length, z),
        (x, y, z + orientation.height),
    ):
        if (
            candidate[0] < bin_capacity.width
            and candidate[1] < bin_capacity.length
            and candidate[2] < bin_capacity.height
        ):
            points.add(candidate)


def greedy_pack(
    items: Sequence[Item],
    bin_capacity: Bin,
    *,
    order: ItemOrder = ItemOrder.VOLUME,
    max_bins: int | None = None,
) -> PackingSolution | None:
    """Pack items with a bottom-left-back first-fit heuristic.

    Returns ``None`` when the packing would need more than ``max_bins`` bins.
    """
    if not items:
        return PackingSolution(bin_count=0, placements=())

    bin_points: list[set[Point]] = []
    bin_placements: list[list[Placement]] = []

    for item in _sorted_items(items, order):
        orientations = allowed_orientations(item, bin_capacity)
        if not orientations:
            return None
        found: tuple[int, Point, Orientation] | None = None
        for index, placements in enumerate(bin_placements):
            position = _first_position(
                bin_capacity, placements, bin_points[index], orientations
            )
            if position is not None:
                found = (index, *position)
                break
        if found is None:
            if max_bins is not None and len(bin_placements) >= max_bins:
                return None
            index = len(bin_placements)
            bin_points.append({(0, 0, 0)})
            bin_placements.append([])
            position = _first_position(
                bin_capacity, [], bin_points[index], orientations
            )
            if position is None:  # pragma: no cover - orientations are pre-filtered
                return None
            found = (index, *position)

        index, (x, y, z), orientation = found
        bin_placements[index].append(
            Placement(
                item_id=item.id,
                bin_index=index,
                x=x,
                y=y,
                z=z,
                width=orientation.width,
                length=orientation.length,
                height=orientation.height,
            )
        )
        _extend_points(bin_capacity, bin_points[index], (x, y, z), orientation)

    placements = tuple(placement for group in bin_placements for placement in group)
    return PackingSolution(bin_count=len(bin_placements), placements=placements)


def best_greedy_pack(
    items: Sequence[Item], bin_capacity: Bin
) -> PackingSolution | None:
    """Run every ordering and keep the packing with the fewest bins."""
    best: PackingSolution | None = None
    for order in ItemOrder:
        candidate = greedy_pack(items, bin_capacity, order=order)
        if candidate is None:
            continue
        if best is None or candidate.bin_count < best.bin_count:
            best = candidate
    return best
