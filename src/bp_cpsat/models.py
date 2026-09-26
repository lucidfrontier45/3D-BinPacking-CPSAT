"""Typed domain objects for the 3D bin-packing problem."""

from __future__ import annotations

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


@dataclass(frozen=True, slots=True)
class Item:
    """A rectangular item to be packed.

    Dimensions are expressed in the item's local frame, before any rotation
    allowed by :attr:`rotation`.
    """

    id: str
    width: int
    length: int
    height: int
    rotation: RotationType = RotationType.NONE

    def __post_init__(self) -> None:
        _require_positive("width", self.width)
        _require_positive("length", self.length)
        _require_positive("height", self.height)
        if not self.id:
            msg = "item id must be non-empty"
            raise ValueError(msg)

    @property
    def volume(self) -> int:
        return self.width * self.length * self.height

    @property
    def base_area(self) -> int:
        return self.width * self.length

    @property
    def max_dimension(self) -> int:
        return max(self.width, self.length, self.height)


@dataclass(frozen=True, slots=True)
class Bin:
    """A bin capacity; all bins of a problem share these dimensions."""

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


@dataclass(frozen=True, slots=True)
class Orientation:
    """An axis-aligned orientation of an item, as (width, length, height)."""

    width: int
    length: int
    height: int

    @property
    def volume(self) -> int:
        return self.width * self.length * self.height

    @property
    def base_area(self) -> int:
        return self.width * self.length

    def as_tuple(self) -> tuple[int, int, int]:
        return (self.width, self.length, self.height)


@dataclass(frozen=True, slots=True)
class Placement:
    """Position of one item inside one bin, using oriented dimensions."""

    item_id: str
    bin_index: int
    x: int
    y: int
    z: int
    width: int
    length: int
    height: int

    @property
    def x_end(self) -> int:
        return self.x + self.width

    @property
    def y_end(self) -> int:
        return self.y + self.length

    @property
    def z_end(self) -> int:
        return self.z + self.height


@dataclass(frozen=True, slots=True)
class PackingSolution:
    """A complete packing: every item appears exactly once."""

    bin_count: int
    placements: tuple[Placement, ...]
