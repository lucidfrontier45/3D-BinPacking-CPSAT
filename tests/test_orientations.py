"""Orientation generation, deduplication and fit filtering."""

from typing import cast

import pytest

from bp_cpsat import Bin, Item, RotationType, allowed_orientations
from bp_cpsat.orientations import candidate_orientations

BIN = Bin(10, 10, 10)


def test_none_produces_exactly_one_orientation() -> None:
    item = Item("a", 3, 4, 5, RotationType.NONE)
    orientations = allowed_orientations(item, BIN)
    assert len(orientations) == 1
    assert orientations[0].as_tuple() == (3, 4, 5)


@pytest.mark.parametrize("rotation", ["none", "fixed_bottom", "all"])
def test_string_rotation_policy_is_coerced_to_enum(rotation: str) -> None:
    item = Item("a", 3, 4, 5, cast(RotationType, rotation))
    assert item.rotation is RotationType(rotation)
    assert len(candidate_orientations(item)) == {
        "none": 1,
        "fixed_bottom": 2,
        "all": 6,
    }[rotation]


def test_invalid_rotation_policy_is_rejected() -> None:
    with pytest.raises(ValueError, match="rotation must be one of"):
        Item("a", 3, 4, 5, cast(RotationType, "invalid"))


def test_fixed_bottom_only_swaps_width_and_length() -> None:
    item = Item("a", 3, 4, 5, RotationType.FIXED_BOTTOM)
    got = {o.as_tuple() for o in allowed_orientations(item, BIN)}
    assert got == {(3, 4, 5), (4, 3, 5)}


def test_all_produces_six_orientations_for_distinct_dimensions() -> None:
    item = Item("a", 3, 4, 5, RotationType.ALL)
    got = {o.as_tuple() for o in allowed_orientations(item, BIN)}
    assert got == {
        (3, 4, 5),
        (3, 5, 4),
        (4, 3, 5),
        (4, 5, 3),
        (5, 3, 4),
        (5, 4, 3),
    }


def test_duplicate_orientations_are_removed() -> None:
    cube = Item("cube", 4, 4, 4, RotationType.ALL)
    assert len(allowed_orientations(cube, BIN)) == 1

    square = Item("square", 4, 4, 7, RotationType.ALL)
    assert len(allowed_orientations(square, BIN)) == 3


def test_orientations_that_do_not_fit_are_removed() -> None:
    bin_capacity = Bin(10, 6, 10)
    item = Item("a", 7, 8, 5, RotationType.ALL)
    got = {o.as_tuple() for o in allowed_orientations(item, bin_capacity)}
    assert len(candidate_orientations(item)) == 6
    assert got == {(7, 5, 8), (8, 5, 7)}


def test_no_orientation_fits_returns_empty() -> None:
    item = Item("a", 12, 8, 5, RotationType.ALL)
    assert allowed_orientations(item, BIN) == ()


def test_candidates_include_duplicates_before_filtering() -> None:
    item = Item("a", 4, 4, 4, RotationType.ALL)
    assert len(candidate_orientations(item)) == 6
    assert len({o.as_tuple() for o in candidate_orientations(item)}) == 1
