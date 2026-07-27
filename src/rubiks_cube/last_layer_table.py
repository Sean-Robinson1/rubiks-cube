"""Precomputed macro solutions for the entire last layer (the yellow face).

Once the F2L is solved, the whole last layer - its 4 corners and 4 edges - is finished here in one
table-driven pass, replacing the previous four looping beginner-method stages. The macros are short
move sequences that are strictly F2L-neutral: applied to a cube of 54 distinct labels, every one of
the 33 non-last-layer stickers returns to its exact home (see _strictNeutral). A permutation that
fixes those positions on distinct labels fixes them from any state, so no macro can ever disturb the
solved F2L - this is what makes the pass provably safe.

Given a solved F2L the last layer has exactly 4! * 3^3 * 4! * 2^3 / 2 = 62,208 reachable states
(the /2 is the corner/edge permutation-parity constraint). Twelve strictly-neutral macros plus the
free bottom turns (D, D', D2) span all of them, so we BFS backward from solved and store, per state,
the macro that steps one closer; solveLastLayer becomes a sequence of O(1) table lookups.

The table (last_layer_table.bin) is generated offline by buildTable (run this module as a
script) and loaded at import.
"""

import heapq
import itertools
import operator
import os

from .constants import RELATIVE_FACE_MAPPING, SOLVED_MASK
from .cube_utils import buildPathTable, deserialisePaths, rotate, serialisePaths

# the four last-layer (yellow/bottom) corner and edge slots, as sticker-index tuples. For every
# corner the last element is the yellow-face sticker; for every edge the second element is.
LL_CORNERS = [(15, 44, 51), (17, 24, 45), (26, 33, 47), (35, 42, 53)]
LL_EDGES = [(16, 48), (25, 46), (34, 50), (43, 52)]

# the number of encodable states (dense index, see encodeLastLayer) and the sentinel for the solved
# state / any unreachable index. Only 62,208 of these indices are reachable; the rest stay NO_MACRO.
TABLE_SIZE = 24 * 81 * 24 * 16
NO_MACRO = 255

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "data", "last_layer_table.bin")

# every sticker index that is NOT part of the last layer - these must be untouched by any macro
_LL_INDICES = {p for slot in LL_CORNERS + LL_EDGES for p in slot}
_NON_LL = [i for i in range(54) if i not in _LL_INDICES]

# a probe "cube" of 54 distinct characters, used to test macros as raw permutations rather than by
# colour (so two identically-coloured F2L stickers swapping cannot masquerade as a no-op)
_PROBE = "".join(chr(33 + i) for i in range(54))


def _invertMove(move: str) -> str:
    return move[0] if move.endswith("'") else move + "'"


def _apply(state: str, tokens: list[str]) -> str:
    for move in tokens:
        state = rotate(state, move)
    return state


def _strictNeutral(tokens: list[str]) -> bool:
    """True if the macro leaves every non-last-layer cubie exactly where it was.

    Tested on the distinct-label probe, so this is a property of the permutation itself and therefore
    holds from any cube state, not just the solved one.
    """
    result = _apply(_PROBE, tokens)
    return all(result[i] == _PROBE[i] for i in _NON_LL)


def _conjugate(face: str, tokens: list[str]) -> list[str]:
    """Rewrites a macro as if performed from a different side face (the same remap
    Cube.convertSequenceFromFace uses), giving the four rotational variants of each base macro."""
    remap = RELATIVE_FACE_MAPPING.get(face, {})
    return [remap.get(move[0], move[0]) + move[1:] for move in tokens]


# base macros, each strictly F2L-neutral: edge orientation, an edge 3-cycle, a corner 3-cycle, and two
# corner-twist commutators. Conjugated onto the four side faces they cover every kind of last-layer
# change; the strict-neutrality filter below is what guarantees safety, so this list is free to grow.
_BASE_MACROS = [
    ["F", "L", "D", "L'", "D'", "F'"],
    ["L", "D", "L'", "D", "L", "D", "D", "L'", "D"],
    ["D", "L", "D'", "R'", "D", "L'", "D'", "R"],
    ["R'", "D'", "R", "D", "R'", "D'", "R", "D"],
    ["R", "D", "R'", "D", "R", "D", "R'", "D"],
]
_FACES = ["R", "B", "G", "O"]

# build the macro set: every strictly-neutral face-variant of every base (de-duplicated, order kept)
# plus the free bottom turns. Filtering here makes F2L-safety a self-enforcing invariant of the table.
MACROS: list[list[str]] = []
_seen_macros = set()
for _base in _BASE_MACROS:
    for _face in _FACES:
        _variant = _conjugate(_face, _base)
        _key = tuple(_variant)
        if _key not in _seen_macros and _strictNeutral(_variant):
            _seen_macros.add(_key)
            MACROS.append(_variant)
MACROS += [["D"], ["D'"], ["D", "D"]]

# the move sequence (as a string) that undoes each macro - applied to step towards the solved layer
INVERSE_MACROS = ["".join(_invertMove(m) for m in reversed(seq)) for seq in MACROS]

# canonical piece ids from the solved cube: a corner is identified by its two non-yellow colours, an
# edge by its one non-yellow colour, so the same piece always maps to the same id regardless of slot
_CORNER_ID = {}
for _slot, _tri in enumerate(LL_CORNERS):
    _CORNER_ID[frozenset(SOLVED_MASK[p] for p in _tri if SOLVED_MASK[p] != "Y")] = _slot
_EDGE_ID = {}
for _slot, (_a, _b) in enumerate(LL_EDGES):
    _EDGE_ID[SOLVED_MASK[_a] if SOLVED_MASK[_b] == "Y" else SOLVED_MASK[_b]] = _slot


def _rank(perm: list[int]) -> int:
    """Lehmer-code rank of a permutation of 0..n-1, giving a dense index in [0, n!)."""
    rank = 0
    n = len(perm)
    for i in range(n):
        smaller = sum(1 for j in range(i + 1, n) if perm[j] < perm[i])
        rank = rank * (n - i) + smaller
    return rank


# fast-encode helpers: gather the 12 corner and 8 edge stickers in one call each, map each slot's
# stickers to its contribution, and turn the four piece ids into a Lehmer rank through a 256-entry
# table keyed by the ids packed as base-4 digits (0-255).
_LL_CORNER_STICKERS = operator.itemgetter(*[p for tri in LL_CORNERS for p in tri])
_LL_EDGE_STICKERS = operator.itemgetter(*[p for pair in LL_EDGES for p in pair])
_LL_CORNER_PAIR = {}
for _pair, _id in _CORNER_ID.items():
    _x, _y = tuple(_pair)
    _LL_CORNER_PAIR[_x + _y] = _id
    _LL_CORNER_PAIR[_y + _x] = _id
_RANK4 = [0] * 256
for _perm in itertools.permutations(range(4)):
    _RANK4[((_perm[0] * 4 + _perm[1]) * 4 + _perm[2]) * 4 + _perm[3]] = _rank(list(_perm))
_POW3 = (1, 3, 9, 27)
_POW2 = (1, 2, 4, 8)


def encodeLastLayer(state: str) -> int:
    """Encodes the last layer of a cube state as a dense integer in [0, TABLE_SIZE).

    The layer is fully described by which piece sits in each of the 4 corner and 4 edge slots and how
    it is oriented, so distinct last layers get distinct indices. Valid once the F2L is solved, which
    confines the last-layer pieces to these eight slots.

    Args:
        state (str): The 54-character cube state string.

    Returns:
        int: The encoded last-layer state.
    """
    corners = _LL_CORNER_STICKERS(state)
    cornerKey = 0
    cornerOri = 0
    for slot in range(4):
        i = slot * 3
        x, y, z = corners[i], corners[i + 1], corners[i + 2]
        if x == "Y":
            pos, pid = 0, _LL_CORNER_PAIR[y + z]
        elif y == "Y":
            pos, pid = 1, _LL_CORNER_PAIR[x + z]
        else:
            pos, pid = 2, _LL_CORNER_PAIR[x + y]
        cornerKey = cornerKey * 4 + pid
        cornerOri += pos * _POW3[slot]

    edges = _LL_EDGE_STICKERS(state)
    edgeKey = 0
    edgeOri = 0
    for slot in range(4):
        a, b = edges[slot * 2], edges[slot * 2 + 1]
        if b == "Y":
            edgeKey = edgeKey * 4 + _EDGE_ID[a]
            edgeOri += _POW2[slot]
        else:
            edgeKey = edgeKey * 4 + _EDGE_ID[b]

    return ((_RANK4[cornerKey] * 81 + cornerOri) * 24 + _RANK4[edgeKey]) * 16 + edgeOri


def buildTable() -> bytearray:
    """Builds the last-layer macro table by move-weighted (Dijkstra) search backwards from solved.

    Each macro edge is weighted by its move length, so every reachable last-layer state stores the
    macro on a *move-shortest* path to solved (its inverse is applied when solving); the solved state
    and unreachable indices keep NO_MACRO.

    Returns:
        bytearray: The macro table of length TABLE_SIZE.
    """
    table = bytearray([NO_MACRO]) * TABLE_SIZE
    distance = [1 << 30] * TABLE_SIZE

    solvedIdx = encodeLastLayer(SOLVED_MASK)
    distance[solvedIdx] = 0
    reps = {solvedIdx: SOLVED_MASK}
    queue = [(0, solvedIdx)]

    while queue:
        dist, idx = heapq.heappop(queue)
        if dist > distance[idx]:
            continue  # stale heap entry
        state = reps[idx]
        for macro, sequence in enumerate(MACROS):
            newState = _apply(state, sequence)
            newIdx = encodeLastLayer(newState)
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
    """Loads the last-layer table, or None if it hasn't been built yet."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return bytearray(handle.read())
    except FileNotFoundError:
        return None


LAST_LAYER_TABLE = _loadTable()

_PATHS_PATH = os.path.join(os.path.dirname(__file__), "data", "last_layer_paths.bin")


def buildPaths(table: bytearray = None) -> dict:
    """Builds the full solution table, mapping every last layer state to the solution for it.

    Args:
        table (bytearray, optional): The macro table to follow. Built if not given.

    Returns:
        dict: Maps each state's index to its permutation and move labels.
    """
    if table is None:
        table = buildTable()
    return buildPathTable(SOLVED_MASK, encodeLastLayer, table, NO_MACRO, MACROS, _apply,
                          lambda macro: INVERSE_MACROS[macro])


def _loadPaths() -> dict | None:
    """Loads the packed last-layer paths, or None if the file is missing."""
    try:
        with open(_PATHS_PATH, "rb") as handle:
            return deserialisePaths(handle.read())
    except FileNotFoundError:
        return None


LAST_LAYER_PATHS = _loadPaths()


if __name__ == "__main__":
    generated = buildTable()
    reachable = sum(1 for b in generated if b != NO_MACRO) + 1  # + the solved state (kept NO_MACRO)
    assert reachable == 62208, f"expected 62208 reachable states, got {reachable}"
    os.makedirs(os.path.dirname(_TABLE_PATH), exist_ok=True)
    with open(_TABLE_PATH, "wb") as handle:
        handle.write(generated)
    print(f"wrote {_TABLE_PATH} ({len(generated)} bytes, {reachable} reachable states, {len(MACROS)} macros)")

    paths = buildPaths(generated)
    with open(_PATHS_PATH, "wb") as handle:
        handle.write(serialisePaths(paths))
    print(f"wrote {_PATHS_PATH} ({len(paths)} states)")
