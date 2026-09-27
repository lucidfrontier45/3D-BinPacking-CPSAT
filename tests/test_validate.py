"""Independent solution validation."""

import pytest

from bp_cpsat import (
    Bin,
    Coordinate,
    Item,
    PackingSolution,
    Placement,
    RotationType,
    Shape,
    validate,
    validation_errors,
)

from bp_cpsat.validate import ValidationError

BIN = Bin(10, 10, 10)
ITEMS = [Item("a", Shape(5, 10, 10)), Item("b", Shape(5, 10, 10))]


def _solution(placements: tuple[Placement, ...], bin_count: int) -> PackingSolution:
    return PackingSolution(bin_count=bin_count, placements=placements)


TOUCHING = _solution(
    (
        Placement("a", 0, Coordinate(0, 0, 0), Shape(5, 10, 10)),
        Placement("b", 0, Coordinate(5, 0, 0), Shape(5, 10, 10)),
    ),
    bin_count=1,
)


def test_valid_solution_has_no_errors() -> None:
    assert validation_errors(ITEMS, BIN, TOUCHING) == ()
    validate(ITEMS, BIN, TOUCHING)


def test_missing_item_is_reported() -> None:
    errors = validation_errors(ITEMS, BIN, _solution(TOUCHING.placements[:1], 1))
    assert any("missing items" in error for error in errors)


def test_overlap_is_reported() -> None:
    overlapping = _solution(
        (
            Placement("a", 0, Coordinate(0, 0, 0), Shape(5, 10, 10)),
            Placement("b", 0, Coordinate(3, 0, 0), Shape(5, 10, 10)),
        ),
        bin_count=1,
    )
    errors = validation_errors(ITEMS, BIN, overlapping)
    assert any("overlap" in error for error in errors)


def test_items_in_different_bins_do_not_overlap() -> None:
    split = _solution(
        (
            Placement("a", 0, Coordinate(0, 0, 0), Shape(5, 10, 10)),
            Placement("b", 1, Coordinate(0, 0, 0), Shape(5, 10, 10)),
        ),
        bin_count=2,
    )
    assert validation_errors(ITEMS, BIN, split) == ()


def test_out_of_bin_placement_is_reported() -> None:
    outside = _solution(
        (
            Placement("a", 0, Coordinate(6, 0, 0), Shape(5, 10, 10)),
            Placement("b", 0, Coordinate(0, 0, 0), Shape(5, 10, 10)),
        ),
        bin_count=1,
    )
    errors = validation_errors(ITEMS, BIN, outside)
    assert any("outside" in error for error in errors)


def test_negative_coordinate_is_rejected_at_construction() -> None:
    """A placement can no longer be built with a negative origin."""
    with pytest.raises(ValueError, match="x must be non-negative"):
        Placement("a", 0, Coordinate(-1, 0, 0), Shape(5, 10, 10))


def test_disallowed_orientation_is_reported() -> None:
    rotated = _solution(
        (
            Placement("a", 0, Coordinate(0, 0, 0), Shape(10, 5, 10)),
            Placement("b", 0, Coordinate(0, 5, 0), Shape(5, 10, 10)),
        ),
        bin_count=1,
    )
    errors = validation_errors(ITEMS, BIN, rotated)
    assert any("disallowed orientation" in error for error in errors)


def test_fixed_bottom_accepts_width_length_swap() -> None:
    items = [Item("a", Shape(5, 8, 10), RotationType.FIXED_BOTTOM)]
    solution = _solution((Placement("a", 0, Coordinate(0, 0, 0), Shape(8, 5, 10)),), 1)
    assert validation_errors(items, BIN, solution) == ()


def test_wrong_bin_count_is_reported() -> None:
    errors = validation_errors(ITEMS, BIN, _solution(TOUCHING.placements, bin_count=3))
    assert any("bin_count" in error for error in errors)


def test_non_consecutive_bin_indices_are_reported() -> None:
    gapped = _solution(
        (
            Placement("a", 0, Coordinate(0, 0, 0), Shape(5, 10, 10)),
            Placement("b", 2, Coordinate(5, 0, 0), Shape(5, 10, 10)),
        ),
        bin_count=3,
    )
    errors = validation_errors(ITEMS, BIN, gapped)
    assert any("consecutive" in error for error in errors)


def test_unknown_item_id_is_reported() -> None:
    alien = _solution((Placement("zzz", 0, Coordinate(0, 0, 0), Shape(1, 1, 1)),), 1)
    errors = validation_errors(ITEMS, BIN, alien)
    assert any("unknown item id" in error for error in errors)
    assert any("missing items" in error for error in errors)


def test_duplicate_item_is_reported() -> None:
    duplicated = _solution(
        (
            Placement("a", 0, Coordinate(0, 0, 0), Shape(5, 10, 10)),
            Placement("a", 0, Coordinate(5, 0, 0), Shape(5, 10, 10)),
        ),
        bin_count=1,
    )
    errors = validation_errors(ITEMS, BIN, duplicated)
    assert any("more than once" in error for error in errors)
    assert any("missing items" in error for error in errors)


def test_validate_raises_with_all_errors_joined() -> None:
    broken = _solution((), bin_count=0)
    with pytest.raises(ValidationError, match="missing items"):
        validate(ITEMS, BIN, broken)
