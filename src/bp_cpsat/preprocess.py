"""Bounds, orientation compatibility and incompatibility graph preprocessing."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
from dataclasses import dataclass

from .models import Bin, Item, Orientation, PackingSolution, Placement
from .orientations import allowed_orientations


class InfeasibleInstanceError(ValueError):
    """Raised before model construction when an item cannot fit in one bin."""


@dataclass(frozen=True, slots=True)
class PreparedItem:
    """An item together with its feasible orientations, in canonical order."""

    item: Item
    orientations: tuple[Orientation, ...]

    @property
    def id(self) -> str:
        return self.item.id

    @property
    def volume(self) -> int:
        return self.item.volume

    @property
    def min_width(self) -> int:
        return min(orientation.width for orientation in self.orientations)

    @property
    def min_length(self) -> int:
        return min(orientation.length for orientation in self.orientations)

    @property
    def min_height(self) -> int:
        return min(orientation.height for orientation in self.orientations)


@dataclass(frozen=True, slots=True)
class PairCompatibility:
    """Precomputed pairwise data for items ``i < j``.

    ``separable`` marks the axes on which *some* orientation pair fits side by
    side; ``allowed[p][q]`` tells whether orientations ``p`` and ``q`` can
    coexist in one bin at all.
    """

    separable: tuple[bool, bool, bool]
    allowed: tuple[tuple[bool, ...], ...]

    @property
    def coexistence_possible(self) -> bool:
        return any(self.separable)


def build_pair_compatibility(
    first: PreparedItem, second: PreparedItem, bin_capacity: Bin
) -> PairCompatibility:
    """Compute axis separability and orientation-pair compatibility for a pair."""
    allowed = tuple(
        tuple(
            first_o.width + second_o.width <= bin_capacity.width
            or first_o.length + second_o.length <= bin_capacity.length
            or first_o.height + second_o.height <= bin_capacity.height
            for second_o in second.orientations
        )
        for first_o in first.orientations
    )
    separable = (
        first.min_width + second.min_width <= bin_capacity.width,
        first.min_length + second.min_length <= bin_capacity.length,
        first.min_height + second.min_height <= bin_capacity.height,
    )
    return PairCompatibility(separable=separable, allowed=allowed)


@dataclass(frozen=True, slots=True)
class PreparedProblem:
    """Everything the model builder needs, computed once per instance."""

    bin_capacity: Bin
    items: tuple[PreparedItem, ...]
    pairs: dict[tuple[int, int], PairCompatibility]
    total_volume: int
    volume_lower_bound: int
    clique_lower_bound: int
    upper_bound: int
    greedy_placements: tuple[Placement, ...]

    @property
    def item_count(self) -> int:
        return len(self.items)

    @property
    def lower_bound(self) -> int:
        return max(self.volume_lower_bound, self.clique_lower_bound)

    def pair(self, i: int, j: int) -> PairCompatibility:
        return self.pairs[(i, j)] if i < j else self.pairs[(j, i)]


def volume_lower_bound(items: Sequence[PreparedItem], bin_capacity: Bin) -> int:
    """``ceil(total item volume / bin volume)``.

    Every item has strictly positive dimensions, so the total is positive for
    any non-empty instance and an empty one cannot reach here.
    """
    return -(-sum(prepared.volume for prepared in items) // bin_capacity.volume)


def _greedy_clique(adjacency: tuple[frozenset[int], ...]) -> int:
    """Largest clique found by growing greedily from every start node."""
    count = len(adjacency)
    if count == 0:
        return 0
    best = 1
    order = sorted(range(count), key=lambda node: (-len(adjacency[node]), node))
    for start in order:
        clique = [start]
        for candidate in order:
            if candidate == start:
                continue
            if all(candidate in adjacency[node] for node in clique):
                clique.append(candidate)
        if len(clique) > best:
            best = len(clique)
    return best


def incompatibility_clique_lower_bound(
    pairs: Mapping[tuple[int, int], PairCompatibility],
    item_count: int,
) -> int:
    """Size of a greedy clique in the pairwise incompatibility graph.

    Reads the precomputed ``pairs`` mapping, so callers that already built the
    pairwise data do not pay for it twice. ``item_count`` sizes the graph; a
    single item is vacuously a clique, so any non-empty instance contributes a
    lower bound of at least one bin.
    """
    if item_count == 0:
        return 0
    adjacency: dict[int, set[int]] = {}
    for (i, j), compatibility in pairs.items():
        if not compatibility.coexistence_possible:
            adjacency.setdefault(i, set()).add(j)
            adjacency.setdefault(j, set()).add(i)
    empty = frozenset[int]()
    dense = tuple(frozenset(adjacency.get(node, empty)) for node in range(item_count))
    return _greedy_clique(dense)


def prepare(
    items: Sequence[Item], bin_capacity: Bin, greedy: PackingSolution
) -> PreparedProblem:
    """Build the canonical, deterministically ordered instance description.

    Raises :class:`InfeasibleInstanceError` when an item cannot fit in a bin.
    """
    if len({item.id for item in items}) != len(items):
        msg = "item ids must be unique"
        raise ValueError(msg)

    ordered = sorted(items, key=lambda item: (-item.volume, item.id))
    prepared_items: list[PreparedItem] = []
    for item in ordered:
        orientations = allowed_orientations(item, bin_capacity)
        if not orientations:
            msg = (
                f"item {item.id!r} does not fit in the bin "
                f"under rotation policy {item.rotation!s}"
            )
            raise InfeasibleInstanceError(msg)
        prepared_items.append(PreparedItem(item=item, orientations=orientations))

    items_tuple = tuple(prepared_items)
    pairs: dict[tuple[int, int], PairCompatibility] = {}
    for i in range(len(items_tuple)):
        for j in range(i + 1, len(items_tuple)):
            pairs[(i, j)] = build_pair_compatibility(
                items_tuple[i], items_tuple[j], bin_capacity
            )

    return PreparedProblem(
        bin_capacity=bin_capacity,
        items=items_tuple,
        pairs=pairs,
        total_volume=sum(prepared.volume for prepared in items_tuple),
        volume_lower_bound=volume_lower_bound(items_tuple, bin_capacity),
        clique_lower_bound=incompatibility_clique_lower_bound(pairs, len(items_tuple)),
        upper_bound=greedy.bin_count,
        greedy_placements=greedy.placements,
    )
