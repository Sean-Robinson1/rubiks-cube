"""Precomputed macro solutions for the F2L middle-edge subproblem.

The four middle-layer (E-slice) edges are solved last in F2L, so their macros must preserve both the
cross and the white corners - the entire top layer. The shortest such cross-and-corner-preserving
move sequences are 6 moves long; together with the free bottom-layer turns (D, D', D2), which
reposition any middle edge displaced into the bottom, they span all 26,880 reachable middle-edge
states. We BFS backward from solved over that space and store, per state, the macro that steps one
closer to solved, so solveF2LMiddlePieces becomes a sequence of table lookups.

The table (middle_table.bin) is generated offline by buildTable (run this module as a script)
and loaded at import.
"""

import heapq
import operator
import os

from .constants import SOLVED_MASK
from .cross_table import EDGES
from .cube_utils import applyMoves, buildPathTable, deserialisePaths, invertMove, serialisePaths

# the eight non-white edge slots (EDGES without the four white ones); the four middle edges live
# among these during solving, sharing them with the not-yet-solved bottom (yellow) edges
NONWHITE_SLOTS = [(a, b) for (a, b) in EDGES if a >= 9 and b >= 9]

# cross-and-corner-preserving macros: the 8 shortest (length-6) middle-edge movers plus the free
# bottom-layer turns. The set is closed under inversion, so the step back towards solved is another
# macro; we store the inverse string per macro.
MACROS = [
    ["F", "D", "R", "F'", "R'", "F'"], ["F", "R", "F", "R'", "D'", "F'"],
    ["L", "D", "F", "L'", "F'", "L'"], ["L", "F", "L", "F'", "D'", "L'"],
    ["R", "D", "B", "R'", "B'", "R'"], ["R", "B", "R", "B'", "D'", "R'"],
    ["B", "D", "L", "B'", "L'", "B'"], ["B", "L", "B", "L'", "D'", "B'"],
    ["D"], ["D'"], ["D", "D"],
]

# number of encodable states and the sentinel stored for the solved state / any unreachable index
TABLE_SIZE = 16**4
NO_MACRO = 255

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "data", "middle_table.bin")


# the move sequence (as a string) that undoes each macro - applied to step towards solved middles
INVERSE_MACROS = ["".join(invertMove(m) for m in reversed(seq)) for seq in MACROS]

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


def encodeMiddles(state: str) -> int:
    """Encodes the four middle (E-slice) edges of a cube state as an integer in [0, 16**4).

    Each middle edge contributes slot * 2 + orientation (0-15), packed as base-16 digits in a
    fixed colour order. Only valid once the cross and corners are solved, which confines the middle
    edges to the eight non-white slots.

    Args:
        state (str): The 54-character cube state string.

    Returns:
        int: The encoded middle-edge state.
    """
    stickers = _MIDDLE_STICKERS(state)
    idx = 0
    for slot in range(8):
        contribution = _MIDDLE_SLOT_LUT[slot].get((stickers[slot * 2], stickers[slot * 2 + 1]))
        if contribution is not None:
            idx += contribution

    return idx


def buildTable() -> bytearray:
    """Builds the middle-edge macro table by move-weighted (Dijkstra) search backwards from solved.

    Each macro edge is weighted by its move length, so every reachable middle-edge state stores the
    macro on a *move-shortest* path to solved (its inverse is applied when solving); the solved state
    and unreachable indices keep NO_MACRO.

    Returns:
        bytearray: The macro table of length TABLE_SIZE.
    """
    table = bytearray([NO_MACRO]) * TABLE_SIZE
    distance = [1 << 30] * TABLE_SIZE

    solvedIdx = encodeMiddles(SOLVED_MASK)
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
            newIdx = encodeMiddles(newState)
            newDistance = dist + len(sequence)
            if newDistance < distance[newIdx]:
                distance[newIdx] = newDistance
                table[newIdx] = macro
                reps[newIdx] = newState
                heapq.heappush(queue, (newDistance, newIdx))

    return table


def _loadTable() -> bytearray | None:
    """Loads the middle table from disk, or None if buildTable hasn't been run."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return bytearray(handle.read())
    except FileNotFoundError:
        return None


MIDDLE_TABLE = _loadTable()

_PATHS_PATH = os.path.join(os.path.dirname(__file__), "data", "middle_paths.bin")


def buildPaths(table: bytearray = None) -> dict:
    """Builds the full-solution table: every middle state -> (permutation, move labels) solving it."""
    if table is None:
        table = buildTable()
    return buildPathTable(SOLVED_MASK, encodeMiddles, table, NO_MACRO, MACROS, applyMoves,
                          lambda macro: INVERSE_MACROS[macro])


def _loadPaths() -> dict | None:
    """Loads the packed middle paths, or None if they haven't been genrated yet."""
    try:
        with open(_PATHS_PATH, "rb") as handle:
            return deserialisePaths(handle.read())
    except FileNotFoundError:
        return None


MIDDLE_PATHS = _loadPaths()


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
