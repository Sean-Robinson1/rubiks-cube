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

import os
from collections import deque

from .constants import POSSIBLE_ROTATIONS, SOLVED_MASK
from .cube_utils import rotate

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


def _invertMove(move: str) -> str:
    return move[0] if move.endswith("'") else move + "'"


# the move sequence (as a string) that undoes each macro - applied to step towards the solved corners
INVERSE_MACROS = ["".join(_invertMove(m) for m in reversed(seq)) for seq in MACROS]

# map each white corner's colour pair to a fixed index, from the solved cube
_ORDER = {}
for _slot, _tri in enumerate(CORNERS):
    _cols = [SOLVED_MASK[p] for p in _tri]
    if "W" in _cols:
        _ORDER[frozenset(c for c in _cols if c != "W")] = len(_ORDER)


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
    slotOri = {}
    for slot, tri in enumerate(CORNERS):
        cols = [state[p] for p in tri]
        if "W" in cols:
            slotOri[_ORDER[frozenset(c for c in cols if c != "W")]] = slot * 3 + cols.index("W")

    idx = 0
    for colour in range(4):
        idx = idx * 24 + slotOri[colour]
    return idx


def buildTable() -> bytearray:
    """Builds the corner macro table by breadth-first search backwards from the solved corners.

    For every reachable corner state, stores the index of the macro that steps one closer to solved
    (its inverse is applied when solving); the solved state and unreachable indices keep NO_MACRO.

    Returns:
        bytearray: The macro table of length TABLE_SIZE.
    """
    table = bytearray([NO_MACRO]) * TABLE_SIZE
    seen = bytearray(TABLE_SIZE)

    solvedIdx = encodeCorners(SOLVED_MASK)
    seen[solvedIdx] = 1
    reps = {solvedIdx: SOLVED_MASK}
    queue = deque([solvedIdx])

    while queue:
        idx = queue.popleft()
        state = reps.pop(idx)
        for macro, sequence in enumerate(MACROS):
            newState = state
            for move in sequence:
                newState = rotate(newState, move)
            newIdx = encodeCorners(newState)
            if not seen[newIdx]:
                seen[newIdx] = 1
                # we reached newIdx from idx via this macro; stepping back towards solved applies its
                # inverse, so store the macro index (INVERSE_MACROS[macro] is used when solving)
                table[newIdx] = macro
                reps[newIdx] = newState
                queue.append(newIdx)

    return table


def _loadTable() -> bytearray | None:
    """Loads the corner table from disk. Returns None when it hasn't been built yet."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return bytearray(handle.read())
    except FileNotFoundError:
        return None


CORNER_TABLE = _loadTable()


if __name__ == "__main__":
    generated = buildTable()
    os.makedirs(os.path.dirname(_TABLE_PATH), exist_ok=True)
    with open(_TABLE_PATH, "wb") as handle:
        handle.write(generated)
    reachable = sum(1 for b in generated if b != NO_MACRO)
    print(f"wrote {_TABLE_PATH} ({len(generated)} bytes, {reachable} reachable states)")
