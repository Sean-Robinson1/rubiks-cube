"""Precomputed optimal-macro solutions for the F2L white-corner subproblem.

Unlike the cross, the corners cannot be solved independently: every corner insertion must leave the
already-solved cross intact. So instead of single moves, we search over a set of *cross-preserving
macros* - short move sequences that return the cross to solved (verified: they only permute corners
and non-cross edges). Because every macro preserves the cross, the cross drops out of the state and
we are left with just the 4 white corners: 8 slots * 3 orientations each, 12*11*10*9 * ... in practice
136,080 reachable states. We BFS backward from solved over that space and store, per state, the macro
that steps one closer to solved, so solveF2LCorners becomes a short sequence of table lookups.

The table (corner_table.bin) is generated offline by buildTable (run this module as a script)
and loaded at import.
"""

import heapq
import operator
import os

from .constants import SOLVED_MASK
from .cube_utils import applyMoves, buildPathTable, deserialisePaths, invertMove, serialisePaths

# The 8 corner cubies as (sticker index, ...) triples, derived from the rotation mappings the same
# way as the edges. The first four (those with a sticker on the white face, indices 0-8) are the
# white corners we solve.
CORNERS = [(0, 9, 38), (2, 29, 36), (6, 11, 18), (8, 20, 27), (15, 44, 51), (17, 24, 45), (26, 33, 47), (35, 42, 53)]

# cross-preserving macros: short move sequences that leave the solved cross unchanged. Each hides a
# corner in a side slot, turns the free bottom (D) layer, and restores it. The set is closed under
# inversion, so the move back towards solved is another macro; we store the inverse string per macro.
MACROS = [
    ["F", "D", "F'"], ["F", "D'", "F'"], ["L", "D", "L'"], ["L", "D'", "L'"],
    ["R", "D", "R'"], ["R", "D'", "R'"], ["B", "D", "B'"], ["B", "D'", "B'"],
    ["F'", "D", "F"], ["F'", "D'", "F"], ["L'", "D", "L"], ["L'", "D'", "L"],
    ["R'", "D", "R"], ["R'", "D'", "R"], ["B'", "D", "B"], ["B'", "D'", "B"],
    ["F", "D", "D", "F'"], ["F", "D'", "F'", "D"], ["L", "D", "D", "L'"], ["L", "D'", "L'", "D"],
    ["R", "D", "D", "R'"], ["R", "D'", "R'", "D"], ["B", "D", "D", "B'"], ["B", "D'", "B'", "D"],
    ["F'", "D", "D", "F"], ["F'", "D", "F", "D'"], ["L'", "D", "D", "L"], ["L'", "D", "L", "D'"],
    ["R'", "D", "D", "R"], ["R'", "D", "R", "D'"], ["B'", "D", "D", "B"], ["B'", "D", "B", "D'"],
]

# number of encodable states and the sentinel stored for the solved state / any unreachable index
TABLE_SIZE = 24**4
NO_MACRO = 255

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "data", "corner_table.bin")


# the move sequence (as a string) that undoes each macro - applied to step towards the solved corners
INVERSE_MACROS = ["".join(invertMove(m) for m in reversed(seq)) for seq in MACROS]

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
_POW24 = (24**3, 24**2, 24, 1)  # place value of each colour bucket (bucket 0 is the most significant)
_CORNER_SLOT_LUT = []
for _slot in range(len(CORNERS)):
    _lut = {}
    for _pair, _bucket in _ORDER.items():
        _a, _b = tuple(_pair)
        for _w in range(3):  # which of the three stickers is white (the orientation)
            _others = [i for i in range(3) if i != _w]
            for _c1, _c2 in ((_a, _b), (_b, _a)):
                _key = [None, None, None]
                _key[_w] = "W"
                _key[_others[0]] = _c1
                _key[_others[1]] = _c2
                _lut[(_key[0], _key[1], _key[2])] = (_slot * 3 + _w) * _POW24[_bucket]
    _CORNER_SLOT_LUT.append(_lut)


def encodeCorners(state: str) -> int:
    """Encodes the four white corners of a cube state as an integer in [0, 24**4).

    Each white corner contributes slot * 3 + orientation (0-23), packed as base-24 digits in a
    fixed colour order, so equal corner configurations map to the same integer regardless of the
    rest of the cube.

    Args:
        state (str): The 54-character cube state string.

    Returns:
        int: The encoded white-corner state.
    """
    cols = _CORNER_STICKERS(state)
    idx = 0
    for slot in range(8):
        i = slot * 3
        contribution = _CORNER_SLOT_LUT[slot].get((cols[i], cols[i + 1], cols[i + 2]))
        if contribution is not None:
            idx += contribution

    return idx


def buildTable() -> bytearray:
    """Builds the corner macro table by move-weighted (Dijkstra) search backwards from solved.

    Each macro edge is weighted by its move length, so every reachable corner state stores the macro
    on a *move-shortest* path to solved (its inverse is applied when solving) - placing the corners in
    as few moves as the macro set allows, rather than in the fewest macros. The solved state and
    unreachable indices keep NO_MACRO.

    Returns:
        bytearray: The macro table of length TABLE_SIZE.
    """
    table = bytearray([NO_MACRO]) * TABLE_SIZE
    distance = [1 << 30] * TABLE_SIZE

    solvedIdx = encodeCorners(SOLVED_MASK)
    distance[solvedIdx] = 0
    reps = {solvedIdx: SOLVED_MASK}
    queue = [(0, solvedIdx)]

    while queue:
        dist, idx = heapq.heappop(queue)
        if dist > distance[idx]:
            continue  # stale heap entry
        state = reps[idx]
        for macro, sequence in enumerate(MACROS):
            newState = applyMoves(state, sequence)
            newIdx = encodeCorners(newState)
            newDistance = dist + len(sequence)
            if newDistance < distance[newIdx]:
                # reached newIdx from idx via this macro; stepping back towards solved applies its
                # inverse, so store the macro index (INVERSE_MACROS[macro] is used when solving)
                distance[newIdx] = newDistance
                table[newIdx] = macro
                reps[newIdx] = newState
                heapq.heappush(queue, (newDistance, newIdx))

    return table


def _loadTable() -> bytearray | None:
    """Loads the corner table from disk. Returns None when it hasn't been built yet."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return bytearray(handle.read())
    except FileNotFoundError:
        return None


CORNER_TABLE = _loadTable()

_PATHS_PATH = os.path.join(os.path.dirname(__file__), "data", "corner_paths.bin")


def buildPaths(table: bytearray = None) -> dict:
    """Builds the full-solution table: every corner state -> (permutation, move labels) solving it."""
    if table is None:
        table = buildTable()
    return buildPathTable(SOLVED_MASK, encodeCorners, table, NO_MACRO, MACROS, applyMoves,
                          lambda macro: INVERSE_MACROS[macro])


def _loadPaths() -> dict | None:
    """Loads the packed corner paths, or None if the file isn't there yet."""
    try:
        with open(_PATHS_PATH, "rb") as handle:
            return deserialisePaths(handle.read())
    except FileNotFoundError:
        return None


CORNER_PATHS = _loadPaths()


if __name__ == "__main__":
    generated = buildTable()
    os.makedirs(os.path.dirname(_TABLE_PATH), exist_ok=True)
    with open(_TABLE_PATH, "wb") as handle:
        handle.write(generated)
    reachable = sum(1 for b in generated if b != NO_MACRO)
    print(f"wrote {_TABLE_PATH} ({len(generated)} bytes, {reachable} reachable states)")

    paths = buildPaths(generated)
    with open(_PATHS_PATH, "wb") as handle:
        handle.write(serialisePaths(paths))
    print(f"wrote {_PATHS_PATH} ({len(paths)} states)")
