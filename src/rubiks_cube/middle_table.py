"""Precomputed macro solutions for the F2L middle-edge subproblem.

The four middle-layer edges are solved last in F2L, so their macros must preserve both the cross and
the white corners - the entire top layer. Those macros are enumerated (see macro_enumeration.py)
rather than written out by hand: 651 of them up to length 8, against the 8 length-6 movers and 3
bottom-layer turns this stage used to search over. They span all 26,880 reachable middle-edge states
either way, but the wider set cuts the average solution from ~23.9 moves to ~17.1. We search backward
from solved over that space, weighting each macro by its move count, and store per state the macro
that steps one closer to solved.

Running this as a script writes middle_table.bin (the search result, one macro per state) and
middle_paths.bin (the composed whole solutions solveF2LMiddlePieces uses). See cross_table.py for
what separates the two.
"""

import itertools
import operator
import os

from .constants import SOLVED_MASK
from .corner_table import CORNERS
from .cross_table import EDGES
from .cube_utils import (
    applyMoves,
    buildGroupLUT,
    buildPathTable,
    buildStageTable,
    deserialisePaths,
    invertMove,
    loadStageTable,
    serialisePaths,
)
from .macro_enumeration import enumerateMacros

# the eight non-white edge slots (EDGES without the four white ones); the four middle edges live
# among these during solving, sharing them with the not-yet-solved bottom (yellow) edges
NONWHITE_SLOTS = [(a, b) for (a, b) in EDGES if a >= 9 and b >= 9]

# A middle-stage macro has to leave the cross and the white corners exactly where it found them; the
# yellow layer is free, since the last-layer stage sorts out whatever state it is left in. Its effect
# is decided by the eight non-white edge slots, which are every slot a middle edge can occupy.
PRESERVED_STICKERS = sorted(
    set([p for (a, b) in EDGES if a < 9 or b < 9 for p in (a, b)] + [p for tri in CORNERS if min(tri) < 9 for p in tri])
)
TRACKED_STICKERS = [p for pair in NONWHITE_SLOTS for p in pair]

# macros run up to twice this; the 8 hand-written movers this replaced were all length 6
MACRO_HALF_DEPTH = 4

# number of encodable states and the sentinel stored for the solved state / any unreachable index
TABLE_SIZE = 16**4
NO_MACRO = 0xFFFF

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "data", "middle_table.bin")


_macros = None
_inverseMacros: list[str] = []


def macros() -> tuple[list, list]:
    """Returns the stage's macros and the move string undoing each of them.

    Enumerating them takes a couple of seconds, and only the table builds ever need them - solving
    reads the path table - so this is done on the first call rather than on import. The enumeration
    is deterministic and ordered, which it has to be: the table stores macro indices, so a rebuilt
    macro set that came out in a different order would not match an existing table.

    Returns:
        tuple[list, list]: The macros, and the inverse move string for each.
    """
    global _macros, _inverseMacros
    if _macros is None:
        _macros = enumerateMacros(PRESERVED_STICKERS, TRACKED_STICKERS, MACRO_HALF_DEPTH)
        _inverseMacros = ["".join(invertMove(m) for m in reversed(seq)) for seq in _macros]
    return _macros, _inverseMacros


# map each middle edge's colour pair to a fixed index, from the solved cube
_ORDER = {}
for _a, _b in NONWHITE_SLOTS:
    _ca, _cb = SOLVED_MASK[_a], SOLVED_MASK[_b]
    if _ca not in "WY" and _cb not in "WY":
        _ORDER[frozenset((_ca, _cb))] = len(_ORDER)

# fast-encode helpers: one gather of the sixteen non-white-slot stickers, plus a per-slot lookup
# from the two stickers a middle edge shows in that slot to its contribution to the index. The
# slot's place value is folded into the table, so encode only has to sum the contributions it
# finds. A slot holding a yellow or white edge will not match, and is skipped.
_MIDDLE_STICKERS = operator.itemgetter(*[p for pair in NONWHITE_SLOTS for p in pair])

# one gather per wide-key group, on the same reasoning as corner_table.py
_MIDDLE_GROUPS = tuple(
    operator.itemgetter(*[p for pair in NONWHITE_SLOTS[i : i + 2] for p in pair])
    for i in range(0, len(NONWHITE_SLOTS), 2)
)
_POW16 = (16**3, 16**2, 16, 1)  # place value of each colour bucket (bucket 0 is the most significant)
_MIDDLE_SLOT_LUT = []
for _slot in range(len(NONWHITE_SLOTS)):
    _lut = {}
    for _pair, _bucket in _ORDER.items():
        _x, _y = tuple(_pair)
        # orientation 0 when the first sticker holds the lexicographically smaller colour
        _lut[(_x, _y)] = (_slot * 2 + (0 if _x < _y else 1)) * _POW16[_bucket]
        _lut[(_y, _x)] = (_slot * 2 + (0 if _y < _x else 1)) * _POW16[_bucket]
    _MIDDLE_SLOT_LUT.append(_lut)

# wide-key encode: the index is a sum of independent per-slot contributions, so the combined
# contribution of a pair of slots is precomputed once, keyed by the four stickers they show together.
# encodeMiddles then sums four wide lookups with no Python loop, for the identical index.
# _MIDDLE_SLOT_KEYS is the exhaustive set of pairs a slot can display: both orders of each non-white
# edge's two colours (its two physical orientations). A yellow edge is absent from _MIDDLE_SLOT_LUT
# and contributes 0, exactly as the per-slot loop skipped it.
_MIDDLE_SLOT_KEYS = {
    perm for _a, _b in NONWHITE_SLOTS for perm in itertools.permutations((SOLVED_MASK[_a], SOLVED_MASK[_b]))
}
_MIDDLE_GROUP_LUT = buildGroupLUT(_MIDDLE_SLOT_LUT, _MIDDLE_SLOT_KEYS)


def encodeMiddles(state: str) -> int:
    """Encodes the four middle (E-slice) edges of a cube state as an integer in [0, 16**4).

    Each middle edge contributes slot * 2 + orientation (0-15), packed as base-16 digits in a
    fixed colour order. Only valid once the cross and corners are solved, which confines the middle
    edges to the eight non-white slots. Computed as four wide-key lookups (one per slot pair) summed.

    Args:
        state (str): The 54-character cube state string.

    Returns:
        int: The encoded middle-edge state.
    """
    return (
        _MIDDLE_GROUP_LUT[0].get(_MIDDLE_GROUPS[0](state), 0)
        + _MIDDLE_GROUP_LUT[1].get(_MIDDLE_GROUPS[1](state), 0)
        + _MIDDLE_GROUP_LUT[2].get(_MIDDLE_GROUPS[2](state), 0)
        + _MIDDLE_GROUP_LUT[3].get(_MIDDLE_GROUPS[3](state), 0)
    )


def buildTable():
    """Builds the middle-edge macro table, inserting the edges in as few moves as the macros allow.

    Returns:
        array: The macro table of length TABLE_SIZE.
    """
    return buildStageTable(SOLVED_MASK, encodeMiddles, TABLE_SIZE, NO_MACRO, macros()[0])


def _loadTable():
    """Loads the middle table from disk, or None if buildTable hasn't been run."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return loadStageTable(handle.read())
    except FileNotFoundError:
        return None


MIDDLE_TABLE = _loadTable()

_PATHS_PATH = os.path.join(os.path.dirname(__file__), "data", "middle_paths.bin")


def buildPaths(table=None) -> dict:
    """Builds the full-solution table: every middle state -> (permutation, move labels) solving it."""
    if table is None:
        table = buildTable()
    stageMacros, inverseMacros = macros()
    return buildPathTable(
        SOLVED_MASK, encodeMiddles, table, NO_MACRO, stageMacros, applyMoves, lambda macro: inverseMacros[macro]
    )


def _loadPaths() -> list:
    """Loads the packed middle paths, or an empty list if they haven't been genrated yet."""
    try:
        with open(_PATHS_PATH, "rb") as handle:
            return deserialisePaths(handle.read(), TABLE_SIZE)
    except FileNotFoundError:
        return []


MIDDLE_PATHS = _loadPaths()


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
