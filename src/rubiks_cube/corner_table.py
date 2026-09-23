"""Precomputed optimal-macro solutions for the F2L white-corner subproblem.

Unlike the cross, the corners cannot be solved independently: every corner insertion must leave the
already-solved cross intact. So instead of single moves, we search over a set of cross-preserving
macros - move sequences that return the cross to solved, enumerated rather than written out by hand
(see macro_enumeration.py). Because every macro preserves the cross, the cross drops out of the state
and we are left with just the 4 white corners: 8 * 7 * 6 * 5 placements times 3**4 orientations, so
136,080 reachable states. We search backward from solved over that space, weighting each macro by its
move count, and store per state the macro that steps one closer to solved. Searching the 347
enumerated macros in place of the 32 hand-written ones cuts the average corner stage from ~14.8
moves to ~12.6.

Running this as a script writes corner_table.bin (the search result, one macro per state) and
corner_paths.bin (the composed whole solutions solveF2LCorners uses). See cross_table.py for what
separates the two.
"""

import itertools
import operator
import os

from .constants import SOLVED_MASK
from .cross_table import EDGES
from .cube_utils import (applyMoves, buildGroupLUT, buildPathTable, buildStageTable,
                         deserialisePaths, invertMove, loadStageTable, serialisePaths)
from .macro_enumeration import enumerateMacros

# The 8 corner cubies as (sticker index, ...) triples, derived from the rotation mappings the same
# way as the edges. The first four (those with a sticker on the white face, indices 0-8) are the
# white corners we solve.
CORNERS = [(0, 9, 38), (2, 29, 36), (6, 11, 18), (8, 20, 27), (15, 44, 51), (17, 24, 45), (26, 33, 47), (35, 42, 53)]

# A corner-stage macro only has to leave the cross where it found it. Its effect is decided by all 24
# corner stickers - every slot a white corner can occupy, not just the four it ends in.
PRESERVED_STICKERS = sorted(p for (a, b) in EDGES if a < 9 or b < 9 for p in (a, b))
TRACKED_STICKERS = [p for tri in CORNERS for p in tri]

# This stage caps macro length rather than search depth. The enumeration finds 23,543 distinct corner
# effects at length 8, far more than a search over 136,080 states can afford to branch over; capping
# at 5 gives 347 macros for a mean of 12.6 moves, where allowing 6 costs three times the build to
# reach 12.1. The half depth stays at 4 even though no macro exceeds 5 moves, because a length-5
# macro is not always splittable into two halves of 3 that are themselves free of same-face repeats -
# dropping to 3 loses 32 of the 347.
MACRO_HALF_DEPTH = 4
MACRO_MAX_LENGTH = 5

# number of encodable states and the sentinel stored for the solved state / any unreachable index
TABLE_SIZE = 24**4
NO_MACRO = 0xFFFF

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "data", "corner_table.bin")


_macros = None
_inverseMacros: list[str] = []


def macros() -> tuple[list, list]:
    """Returns the stage's macros and the move string undoing each of them.

    Enumerating them takes a second or so, and only the table builds ever need them - solving reads
    the path table - so this happens on the first call rather than on import. The enumeration is
    deterministic and ordered, which it has to be: the table stores macro indices, so a macro set
    that came out in a different order would not match an existing table.

    Returns:
        tuple[list, list]: The macros, and the inverse move string for each.
    """
    global _macros, _inverseMacros
    if _macros is None:
        _macros = enumerateMacros(PRESERVED_STICKERS, TRACKED_STICKERS, MACRO_HALF_DEPTH,
                                  MACRO_MAX_LENGTH)
        _inverseMacros = ["".join(invertMove(m) for m in reversed(seq)) for seq in _macros]
    return _macros, _inverseMacros


# map each white corner's colour pair to a fixed index, from the solved cube
_ORDER = {}
for _slot, _tri in enumerate(CORNERS):
    _cols = [SOLVED_MASK[p] for p in _tri]
    if "W" in _cols:
        _ORDER[frozenset(c for c in _cols if c != "W")] = len(_ORDER)

# fast-encode helpers: one gather of all 24 corner stickers, plus a per-slot lookup from the three
# stickers a white corner shows in that slot to its contribution to the index. The slot's place
# value is folded into the table, so encode only has to sum the contributions it finds. A slot
# holding a yellow corner will not match, and is skipped.
_CORNER_STICKERS = operator.itemgetter(*[p for tri in CORNERS for p in tri])

# one gather per wide-key group, reading that group's six stickers straight out of the state.
# Gathering all 24 and slicing instead allocated a throwaway tuple per group, four an encode.
_CORNER_GROUPS = tuple(operator.itemgetter(*[p for tri in CORNERS[i:i + 2] for p in tri])
                       for i in range(0, len(CORNERS), 2))
_POW24 = (24**3, 24**2, 24, 1)  # place value of each colour bucket (bucket 0 is the most significant)
_CORNER_SLOT_LUT = []
for _slot in range(len(CORNERS)):
    _lut = {}
    for _pair, _bucket in _ORDER.items():
        _a, _b = tuple(_pair)
        for _w in range(3):  # which of the three stickers is white (the orientation)
            _others = [i for i in range(3) if i != _w]
            for _c1, _c2 in ((_a, _b), (_b, _a)):
                _key: list[str | None] = [None, None, None]
                _key[_w] = "W"
                _key[_others[0]] = _c1
                _key[_others[1]] = _c2
                _lut[(_key[0], _key[1], _key[2])] = (_slot * 3 + _w) * _POW24[_bucket]
    _CORNER_SLOT_LUT.append(_lut)

# wide-key encode: the index is a sum of independent per-slot contributions, so the combined
# contribution of a pair of slots is precomputed once, keyed by the six stickers they show together.
# encodeCorners then sums four wide lookups with no Python loop, for the identical index.
# _CORNER_SLOT_KEYS is the exhaustive set of triples a corner slot can display: every ordering of each
# corner cubie's three colours - a superset of its three physical orientations, so no key is missed
# (impossible orderings never occur, so their group entries are harmless). A yellow corner is absent
# from _CORNER_SLOT_LUT and contributes 0, exactly as the per-slot loop skipped it.
_CORNER_SLOT_KEYS = {perm for _tri in CORNERS
                     for perm in itertools.permutations(SOLVED_MASK[p] for p in _tri)}
_CORNER_GROUP_LUT = buildGroupLUT(_CORNER_SLOT_LUT, _CORNER_SLOT_KEYS)


def encodeCorners(state: str) -> int:
    """Encodes the four white corners of a cube state as an integer in [0, 24**4).

    Each white corner contributes slot * 3 + orientation (0-23), packed as base-24 digits in a
    fixed colour order, so equal corner configurations map to the same integer regardless of the
    rest of the cube. Computed as four wide-key lookups (one per slot pair) summed together.

    Args:
        state (str): The 54-character cube state string.

    Returns:
        int: The encoded white-corner state.
    """
    return (_CORNER_GROUP_LUT[0].get(_CORNER_GROUPS[0](state), 0)
            + _CORNER_GROUP_LUT[1].get(_CORNER_GROUPS[1](state), 0)
            + _CORNER_GROUP_LUT[2].get(_CORNER_GROUPS[2](state), 0)
            + _CORNER_GROUP_LUT[3].get(_CORNER_GROUPS[3](state), 0))


def buildTable():
    """Builds the corner macro table, placing the corners in as few moves as the macro set allows.

    Returns:
        array: The macro table of length TABLE_SIZE.
    """
    return buildStageTable(SOLVED_MASK, encodeCorners, TABLE_SIZE, NO_MACRO, macros()[0])


def _loadTable():
    """Loads the corner table from disk. Returns None when it hasn't been built yet."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return loadStageTable(handle.read())
    except FileNotFoundError:
        return None


CORNER_TABLE = _loadTable()

_PATHS_PATH = os.path.join(os.path.dirname(__file__), "data", "corner_paths.bin")


def buildPaths(table=None) -> dict:
    """Builds the full-solution table: every corner state -> (permutation, move labels) solving it."""
    if table is None:
        table = buildTable()
    stageMacros, inverseMacros = macros()
    return buildPathTable(SOLVED_MASK, encodeCorners, table, NO_MACRO, stageMacros, applyMoves,
                          lambda macro: inverseMacros[macro])


def _loadPaths() -> list:
    """Loads the packed corner paths, or an empty list if the file isn't there yet."""
    try:
        with open(_PATHS_PATH, "rb") as handle:
            return deserialisePaths(handle.read(), TABLE_SIZE)
    except FileNotFoundError:
        return []


CORNER_PATHS = _loadPaths()


if __name__ == "__main__":
    print(f"enumerated {len(macros()[0])} macros")
    generated = buildTable()
    os.makedirs(os.path.dirname(_TABLE_PATH), exist_ok=True)
    with open(_TABLE_PATH, "wb") as handle:
        handle.write(generated.tobytes())
    reachable = sum(1 for b in generated if b != NO_MACRO)
    print(f"wrote {_TABLE_PATH} ({len(generated)} states, {reachable} reachable)")

    paths = buildPaths(generated)
    with open(_PATHS_PATH, "wb") as handle:
        handle.write(serialisePaths(paths))
    print(f"wrote {_PATHS_PATH} ({len(paths)} states)")
