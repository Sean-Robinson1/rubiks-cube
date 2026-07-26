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

import operator
import os
from collections import deque

from .constants import SOLVED_MASK
from .cross_table import EDGES
from .cube_utils import rotate

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


def _invertMove(move: str) -> str:
    return move[0] if move.endswith("'") else move + "'"


# the move sequence (as a string) that undoes each macro - applied to step towards solved middles
INVERSE_MACROS = ["".join(_invertMove(m) for m in reversed(seq)) for seq in MACROS]

# map each middle edge's colour pair to a fixed index, from the solved cube
_ORDER = {}
for _a, _b in NONWHITE_SLOTS:
    _ca, _cb = SOLVED_MASK[_a], SOLVED_MASK[_b]
    if _ca not in "WY" and _cb not in "WY":
        _ORDER[frozenset((_ca, _cb))] = len(_ORDER)

# fast-encode helpers: one gather of the sixteen non-white-slot stickers, plus a per-slot lookup
# from the two stickers a middle edge shows in that slot to its colour bucket and orientation. A
# slot holding a yellow or white edge will not match, and is skipped.
_MIDDLE_STICKERS = operator.itemgetter(*[p for pair in NONWHITE_SLOTS for p in pair])
_MIDDLE_PAIR = {}
for _pair, _bucket in _ORDER.items():
    _x, _y = tuple(_pair)
    _MIDDLE_PAIR[_x + _y] = _bucket
    _MIDDLE_PAIR[_y + _x] = _bucket
_WY = frozenset("WY")


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
    digits = [0, 0, 0, 0]
    for slot in range(8):
        a, b = stickers[slot * 2], stickers[slot * 2 + 1]
        if a in _WY or b in _WY:
            continue
        # orientation 0 when the first sticker holds the lexicographically smaller colour
        digits[_MIDDLE_PAIR[a + b]] = slot * 2 + (0 if a < b else 1)

    return ((digits[0] * 16 + digits[1]) * 16 + digits[2]) * 16 + digits[3]


def buildTable() -> bytearray:
    """Builds the middle-edge macro table by breadth-first search backwards from solved.

    For every reachable middle-edge state, stores the index of the macro that steps one closer to
    solved (its inverse is applied when solving); the solved state and unreachable indices keep
    NO_MACRO.

    Returns:
        bytearray: The macro table of length TABLE_SIZE.
    """
    table = bytearray([NO_MACRO]) * TABLE_SIZE
    seen = bytearray(TABLE_SIZE)

    solvedIdx = encodeMiddles(SOLVED_MASK)
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
            newIdx = encodeMiddles(newState)
            if not seen[newIdx]:
                seen[newIdx] = 1
                table[newIdx] = macro
                reps[newIdx] = newState
                queue.append(newIdx)

    return table


def _loadTable() -> bytearray | None:
    """Loads the middle table from disk, or None if buildTable hasn't been run."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return bytearray(handle.read())
    except FileNotFoundError:
        return None


MIDDLE_TABLE = _loadTable()


if __name__ == "__main__":
    generated = buildTable()
    os.makedirs(os.path.dirname(_TABLE_PATH), exist_ok=True)
    with open(_TABLE_PATH, "wb") as handle:
        handle.write(generated)
    reachable = sum(1 for b in generated if b != NO_MACRO)
    print(f"wrote {_TABLE_PATH} ({len(generated)} bytes, {reachable} reachable states)")
