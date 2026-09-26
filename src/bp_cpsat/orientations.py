"""Orientation generation, deduplication and fit filtering."""

from __future__ import annotations

from .models import Bin, Item, Orientation, RotationType

_PERMUTATIONS: tuple[tuple[int, int, int], ...] = (
    (0, 1, 2),
    (0, 2, 1),
    (1, 0, 2),
    (1, 2, 0),
    (2, 0, 1),
    (2, 1, 0),
)


def candidate_orientations(item: Item) -> tuple[Orientation, ...]:
    """Return every orientation allowed by ``item.rotation``, duplicates included."""
    dims = (item.width, item.length, item.height)
    if item.rotation is RotationType.NONE:
        return (Orientation(*dims),)
    if item.rotation is RotationType.FIXED_BOTTOM:
        return (
            Orientation(dims[0], dims[1], dims[2]),
            Orientation(dims[1], dims[0], dims[2]),
        )
    return tuple(Orientation(*(dims[i] for i in perm)) for perm in _PERMUTATIONS)


def allowed_orientations(item: Item, bin_capacity: Bin) -> tuple[Orientation, ...]:
    """Return the deduplicated orientations of ``item`` that fit inside ``bin``.

    Order is deterministic and follows generation order.
    """
    seen: dict[tuple[int, int, int], None] = {}
    for orientation in candidate_orientations(item):
        key = orientation.as_tuple()
        if key in seen:
            continue
        if (
            orientation.width > bin_capacity.width
            or orientation.length > bin_capacity.length
            or orientation.height > bin_capacity.height
        ):
            continue
        seen[key] = None
    return tuple(Orientation(*key) for key in seen)
