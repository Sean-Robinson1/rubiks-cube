"""Precomputed optimal solutions for the white-cross subproblem.

The white cross is only four edges, so its state space is tiny (~12*11*10*9 * 2**4 = 190,080
reachable states). We encode each state as a small integer and store the index of the next move on
an optimal path to the solved cross, in place of what used to be a depth-5 search.

Running this module as a script generates two files, and the other three stage tables are split the
same way. cross_table.bin is the search result itself: one byte per state, naming the single move
that steps that state closer to solved, so solving from it alone would mean a loop - look up, apply
one move, re-encode, repeat. cross_paths.bin walks those single steps all the way to solved for
every state and composes each whole walk into one permutation plus its move labels. That is what
solveCross uses, and why a stage costs one lookup rather than a loop. The table is still shipped
because the paths are rebuilt from it without redoing the search.
"""

import os
from collections import deque

from .constants import POSSIBLE_ROTATIONS, SOLVED_MASK
from .cube_utils import buildPathTable, deserialisePaths, rotate, serialisePaths

# The 12 edges as (sticker index, partner sticker index). Derived from the rotation mappings: a real
# edge's two stickers always move together, so starting from every cross-face sticker pair and
# pruning any pair whose image under some move isn't also a pair converges to exactly these 12.
# White edges are the four with a sticker on the white face (indices 0-8).
EDGES = [(1, 37), (3, 10), (5, 28), (7, 19), (12, 41), (14, 21), (16, 48), (23, 30), (25, 46), (32, 39), (34, 50), (43, 52)]

# the four non-white colours of the cross edges, in a fixed order used to pack the encoding
CROSS_COLOURS = "GRBO"

# number of encodable states, and the sentinel stored for the solved state / any unreachable index
TABLE_SIZE = 24**4
NO_MOVE = 255

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "data", "cross_table.bin")


def encodeCross(state: str) -> int:
    """Encodes the white-cross configuration of a cube state as an integer in [0, 24**4).

    For each white edge, we assign that base-24 encoded digit to be the edges slot,
    which one of the 12 possible edge locations it can be, * 2 + the orientation,
    (if the white is the first one).

    Since there are 12 slots and orientation is a boolean, we get a max value of:

        slot * 2 + orientiation = 11 * 2 + 1 = 23

    (given 0 indexing). This allows us to represnt the state as a base 24 number.  

    Args:
        state (str): The 54-character cube state string.

    Returns:
        int: The encoded white-cross state.
    """
    slotOri = {}
    for slot, (a, b) in enumerate(EDGES):
        if state[a] == "W":
            slotOri[state[b]] = slot * 2
        elif state[b] == "W":
            slotOri[state[a]] = slot * 2 + 1

    idx = 0
    for colour in CROSS_COLOURS:
        idx = idx * 24 + slotOri[colour]
    return idx


def buildTable() -> bytearray:
    """Builds the cross move table by breadth-first search backwards from the solved cross.

    For every reachable cross state, stores the index (into POSSIBLE_ROTATIONS) of a move that
    steps one closer to solved; the solved state and unreachable indices keep the NO_MOVE sentinel.

    Returns:
        bytearray: The move table of length TABLE_SIZE.
    """
    table = bytearray([NO_MOVE]) * TABLE_SIZE
    seen = bytearray(TABLE_SIZE)

    solvedIdx = encodeCross(SOLVED_MASK)
    seen[solvedIdx] = 1
    reps = {solvedIdx: SOLVED_MASK}
    queue = deque([solvedIdx])

    while queue:
        idx = queue.popleft()
        state = reps.pop(idx)
        for move, rotation in enumerate(POSSIBLE_ROTATIONS):
            newState = rotate(state, rotation)
            newIdx = encodeCross(newState)
            if not seen[newIdx]:
                seen[newIdx] = 1
                # we reached newIdx from idx via `rotation`; the move back towards solved is its
                # inverse, which for POSSIBLE_ROTATIONS (6 clockwise then their 6 inverses) is (move+6)%12
                table[newIdx] = (move + 6) % 12
                reps[newIdx] = newState
                queue.append(newIdx)

    return table


def _loadTable() -> bytearray | None:
    """Reads back the cross table writen by the last buildTable run, or None if there isn't one."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return bytearray(handle.read())
    except FileNotFoundError:
        return None


CROSS_TABLE = _loadTable()

_PATHS_PATH = os.path.join(os.path.dirname(__file__), "data", "cross_paths.bin")


def buildPaths(table: bytearray = None) -> dict:
    """Builds the full-solution table: every cross state -> (permutation, move labels) solving it."""
    if table is None:
        table = buildTable()
    return buildPathTable(SOLVED_MASK, encodeCross, table, NO_MOVE, POSSIBLE_ROTATIONS, rotate,
                          lambda move: POSSIBLE_ROTATIONS[move])


def _loadPaths() -> dict | None:
    """Reads back the packed cross paths, or None if they haven't been built yet."""
    try:
        with open(_PATHS_PATH, "rb") as handle:
            return deserialisePaths(handle.read())
    except FileNotFoundError:
        return None


CROSS_PATHS = _loadPaths()


if __name__ == "__main__":
    generated = buildTable()
    os.makedirs(os.path.dirname(_TABLE_PATH), exist_ok=True)
    with open(_TABLE_PATH, "wb") as handle:
        handle.write(generated)
    reachable = sum(1 for b in generated if b != NO_MOVE)
    print(f"wrote {_TABLE_PATH} ({len(generated)} bytes, {reachable} reachable states)")

    paths = buildPaths(generated)
    with open(_PATHS_PATH, "wb") as handle:
        handle.write(serialisePaths(paths))
    print(f"wrote {_PATHS_PATH} ({len(paths)} states)")
