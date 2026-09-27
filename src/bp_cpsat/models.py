"""Typed domain objects for the 3D bin-packing problem."""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from enum import StrEnum


class RotationType(StrEnum):
    """Per-item rotation policy."""

    NONE = "none"
    FIXED_BOTTOM = "fixed_bottom"
    ALL = "all"


def _require_positive(name: str, value: int) -> None:
    if value <= 0:
        msg = f"{name} must be positive, got {value}"
        raise ValueError(msg)


def _require_non_negative(name: str, value: int) -> None:
    if value < 0:
        msg = f"{name} must be non-negative, got {value}"
        raise ValueError(msg)


@dataclass(frozen=True, slots=True)
class Shape:
    """An axis-aligned box size, always ordered ``(width, length, height)``.

    A shape is pure extent: it says how large a box is, never where it sits. The
    same type describes an item's local dimensions, an item's chosen orientation
    and a bin's capacity.
    """

    width: int
    length: int
    height: int

    def __post_init__(self) -> None:
        _require_positive("width", self.width)
        _require_positive("length", self.length)
        _require_positive("height", self.height)

    @property
    def volume(self) -> int:
        return self.width * self.length * self.height

    @property
    def base_area(self) -> int:
        return self.width * self.length

    @property
    def max_dimension(self) -> int:
        return max(self.width, self.length, self.height)

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.width, self.length, self.height)

    def fits_in(self, container: Shape) -> bool:
        """Whether this shape fits inside ``container`` on every axis."""
        return (
            self.width <= container.width
            and self.length <= container.length
            and self.height <= container.height
        )

    def separable_within(self, other: Shape, container: Shape) -> tuple[bool, bool, bool]:
        """Per-axis test of the two shapes fitting side by side inside ``container``."""
        return (
            self.width + other.width <= container.width,
            self.length + other.length <= container.length,
            self.height + other.height <= container.height,
        )

    def fits_beside(self, other: Shape, container: Shape) -> bool:
        """Whether both shapes fit side by side inside ``container`` on some axis."""
        return any(self.separable_within(other, container))

    @staticmethod
    def componentwise_min(shapes: Sequence[Shape]) -> Shape:
        """Per-axis minimum over ``shapes``; raises on an empty sequence."""
        if not shapes:
            msg = "componentwise_min requires at least one shape"
            raise ValueError(msg)
        return Shape(
            width=min(shape.width for shape in shapes),
            length=min(shape.length for shape in shapes),
            height=min(shape.height for shape in shapes),
        )

    @staticmethod
    def componentwise_max(shapes: Sequence[Shape]) -> Shape:
        """Per-axis maximum over ``shapes``; raises on an empty sequence."""
        if not shapes:
            msg = "componentwise_max requires at least one shape"
            raise ValueError(msg)
        return Shape(
            width=max(shape.width for shape in shapes),
            length=max(shape.length for shape in shapes),
            height=max(shape.height for shape in shapes),
        )


#: An item's orientation is just a shape expressed in bin-space axes.
Orientation = Shape


@dataclass(frozen=True, slots=True)
class Bin(Shape):
    """A bin capacity; all bins of a problem share this shape."""


@dataclass(frozen=True, slots=True)
class Coordinate:
    """A corner point in bin space, as non-negative ``(x, y, z)`` offsets."""

    x: int
    y: int
    z: int

    def __post_init__(self) -> None:
        _require_non_negative("x", self.x)
        _require_non_negative("y", self.y)
        _require_non_negative("z", self.z)

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.x, self.y, self.z)

    def offset(self, dx: int, dy: int, dz: int) -> Coordinate:
        """Return this point translated by ``(dx, dy, dz)``."""
        return Coordinate(x=self.x + dx, y=self.y + dy, z=self.z + dz)

    def end(self, shape: Shape) -> Coordinate:
        """Return the exclusive far corner of a box of ``shape`` anchored here."""
        return self.offset(shape.width, shape.length, shape.height)

    def lies_within(self, container: Shape) -> bool:
        """Whether this point is strictly inside ``container``, ignoring extent."""
        return self.x < container.width and self.y < container.length and self.z < container.height

    def fits_box(self, shape: Shape, container: Shape) -> bool:
        """Whether a box of ``shape`` anchored at this point fits inside ``container``."""
        end = self.end(shape)
        return end.x <= container.width and end.y <= container.length and end.z <= container.height


@dataclass(frozen=True, slots=True)
class Item:
    """A rectangular item to be packed.

    ``shape`` holds the item's local dimensions, before any rotation allowed by
    :attr:`rotation`.
    """

    id: str
    shape: Shape
    rotation: RotationType = RotationType.NONE

    def __post_init__(self) -> None:
        if not self.id:
            msg = "item id must be non-empty"
            raise ValueError(msg)
        try:
            rotation = RotationType(self.rotation)
        except (TypeError, ValueError) as error:
            choices = [policy.value for policy in RotationType]
            msg = f"rotation must be one of {choices}, got {self.rotation!r}"
            raise ValueError(msg) from error
        object.__setattr__(self, "rotation", rotation)

    @property
    def volume(self) -> int:
        return self.shape.volume

    @property
    def base_area(self) -> int:
        return self.shape.base_area

    @property
    def max_dimension(self) -> int:
        return self.shape.max_dimension


def boxes_overlap(
    first_origin: Coordinate,
    first_shape: Shape,
    second_origin: Coordinate,
    second_shape: Shape,
) -> bool:
    """Whether two boxes intersect; boxes that merely touch faces do not."""
    first_end = first_origin.end(first_shape)
    second_end = second_origin.end(second_shape)
    return (
        first_origin.x < second_end.x
        and second_origin.x < first_end.x
        and first_origin.y < second_end.y
        and second_origin.y < first_end.y
        and first_origin.z < second_end.z
        and second_origin.z < first_end.z
    )


@dataclass(frozen=True, slots=True)
class Placement:
    """One item put at a bin-space origin, occupying an oriented ``shape``."""

    item_id: str
    bin_index: int
    origin: Coordinate
    shape: Shape

    @property
    def corner(self) -> Coordinate:
        """The exclusive far corner of the placed box."""
        return self.origin.end(self.shape)

    def fits_in(self, bin_capacity: Bin) -> bool:
        return self.origin.fits_box(self.shape, bin_capacity)

    def overlaps(self, other: Placement) -> bool:
        """Whether two placements in the same bin intersect."""
        if self.bin_index != other.bin_index:
            return False
        return boxes_overlap(self.origin, self.shape, other.origin, other.shape)


@dataclass(frozen=True, slots=True)
class PackingSolution:
    """A complete packing: every item appears exactly once.

    ``optimal`` is ``True`` only when ``bin_count`` was proven minimal. It is
    ``False`` when the search stopped on a search limit before ruling out a
    smaller bin count, in which case ``bin_count`` is a valid packing whose
    minimality is unknown.
    """

    bin_count: int
    placements: tuple[Placement, ...]
    optimal: bool = False
