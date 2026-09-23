"""Precomputed macro solutions for the entire last layer (the yellow face).

Once the F2L is solved, the whole last layer - its 4 corners and 4 edges - is finished here in one
table-driven pass, replacing the previous four looping beginner-method stages. The macros are move
sequences that are strictly F2L-neutral: applied to a cube of 54 distinct labels, every one of the
34 non-last-layer stickers returns to its exact home (see _strictNeutral). A permutation that fixes
those positions on distinct labels fixes them from any state, so no macro can disturb the solved F2L.

Given a solved F2L the last layer has exactly 4! * 3^3 * 4! * 2^3 / 2 = 62,208 reachable states
(the /2 is the corner/edge permutation-parity constraint). The macros are enumerated rather than
written by hand (see macro_enumeration.py): 147 of them up to length 8, against the 15 hand-written
ones this replaced. Both sets span the whole space, but searching the wider one cuts the average
last layer from ~31.4 moves to ~19.7. We search backward from solved, weighting each macro by its
move count, and store per state the macro that steps one closer.

Running this as a script writes last_layer_table.bin (the search result, one macro per state) and
last_layer_paths.bin (the composed whole solutions solveLastLayer uses). See cross_table.py for what
separates the two. The paths here are keyed by the 20 last-layer stickers rather than the encode
index, so solving needs no encode step at all.
"""

import itertools
import operator
import os

from .constants import SOLVED_MASK
from .cube_utils import (applyMoves, buildPathTable, buildStageTable, deserialiseKeyedPaths,
                         invertMove, loadStageTable, serialiseKeyedPaths)
from .macro_enumeration import enumerateMacros

# the four last-layer (yellow/bottom) corner and edge slots, as sticker-index tuples. For every
# corner the last element is the yellow-face sticker; for every edge the second element is.
LL_CORNERS = [(15, 44, 51), (17, 24, 45), (26, 33, 47), (35, 42, 53)]
LL_EDGES = [(16, 48), (25, 46), (34, 50), (43, 52)]

# the number of encodable states (dense index, see encodeLastLayer) and the sentinel for the solved
# state / any unreachable index. Only 62,208 of these indices are reachable; the rest stay NO_MACRO.
TABLE_SIZE = 24 * 81 * 24 * 16
NO_MACRO = 0xFFFF

_TABLE_PATH = os.path.join(os.path.dirname(__file__), "data", "last_layer_table.bin")

# every sticker index that is NOT part of the last layer - these must be untouched by any macro
_LL_INDICES = {p for slot in LL_CORNERS + LL_EDGES for p in slot}
_NON_LL = [i for i in range(54) if i not in _LL_INDICES]

# a probe "cube" of 54 distinct characters, used to test macros as raw permutations rather than by
# colour (so two identically-coloured F2L stickers swapping cannot masquerade as a no-op)
_PROBE = "".join(chr(33 + i) for i in range(54))


def _strictNeutral(tokens: list[str]) -> bool:
    """True if the macro leaves every non-last-layer cubie exactly where it was.

    Tested on the distinct-label probe, so this is a property of the permutation itself and therefore
    holds from any cube state, not just the solved one.
    """
    result = applyMoves(_PROBE, tokens)
    return all(result[i] == _PROBE[i] for i in _NON_LL)


# A last-layer macro's effect is decided by the 20 last-layer stickers; everything else is preserved.
# macros run up to twice this depth, which reaches the length-8 algorithms the layer needs.
TRACKED_STICKERS = ([p for tri in LL_CORNERS for p in tri] + [p for pair in LL_EDGES for p in pair])
MACRO_HALF_DEPTH = 4

_macros = None
_inverseMacros: list[str] = []


def macros() -> tuple[list, list]:
    """Returns the stage's macros and the move string undoing each of them.

    Enumerating them takes a couple of seconds and only the table builds need them - solving reads
    the path table - so it happens on the first call rather than on import. The enumeration is
    deterministic and ordered, which it has to be, since the table stores macro indices.

    Every macro is strictly F2L-neutral by construction: the enumeration only joins half-sequences
    whose composition fixes each of _NON_LL, which is the same permutation-level test _strictNeutral
    applies, so no macro can disturb the F2L from any state.

    Returns:
        tuple[list, list]: The macros, and the inverse move string for each.
    """
    global _macros, _inverseMacros
    if _macros is None:
        _macros = enumerateMacros(_NON_LL, TRACKED_STICKERS, MACRO_HALF_DEPTH)
        _inverseMacros = ["".join(invertMove(m) for m in reversed(seq)) for seq in _macros]
    return _macros, _inverseMacros


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

# Once the F2L is solved the 20 last-layer stickers describe the last layer uniquely, so the
# gathered sticker tuple can stand in for the encode index. The solver keys the path table by that
# tuple directly; encodeLastLayer is still what builds the table.
_LL_KEY_POSITIONS = [p for tri in LL_CORNERS for p in tri] + [p for pair in LL_EDGES for p in pair]
_LL_KEY_LENGTH = len(_LL_KEY_POSITIONS)
LAST_LAYER_KEY = operator.itemgetter(*_LL_KEY_POSITIONS)
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
_KEYPLACE = (64, 16, 4, 1)  # base-4 place value of each slot in the packed piece-id key (slot 0 most significant)

# Per-slot lookup tables, one dict.get per slot. A corner slot's three stickers (exactly one is the
# yellow-face sticker) map to the piece id shifted into this slot's base-4 place, and the yellow
# sticker's position (0/1/2) scaled by this slot's base-3 place.
_LL_CORNER_LUT = []
for _slot in range(4):
    _lut = {}
    for _cc, _cid in _LL_CORNER_PAIR.items():  # _cc is a 2-char string of the two non-yellow colours
        _c1, _c2 = _cc[0], _cc[1]
        _keyPart = _cid * _KEYPLACE[_slot]
        _lut[("Y", _c1, _c2)] = (_keyPart, 0)                 # yellow sticker first  -> pos 0
        _lut[(_c1, "Y", _c2)] = (_keyPart, 1 * _POW3[_slot])  # yellow sticker middle -> pos 1
        _lut[(_c1, _c2, "Y")] = (_keyPart, 2 * _POW3[_slot])  # yellow sticker last   -> pos 2
    _LL_CORNER_LUT.append(_lut)

# An edge slot's two stickers map likewise to the edge id in this slot's base-4 place, and this
# slot's flip bit, set only when the yellow sticker is on the yellow-face side.
_LL_EDGE_LUT = []
for _slot in range(4):
    _lut = {}
    for _colour, _eid in _EDGE_ID.items():
        _keyPart = _eid * _KEYPLACE[_slot]
        _lut[(_colour, "Y")] = (_keyPart, _POW2[_slot])  # yellow on the yellow-face side -> flipped
        _lut[("Y", _colour)] = (_keyPart, 0)             # yellow on the other side       -> not flipped
    _LL_EDGE_LUT.append(_lut)


def encodeLastLayer(state: str) -> int:
    """Encodes the last layer of a cube state as a dense integer in [0, TABLE_SIZE).

    All eight last-layer pieces are tracked at once, so rather than one slot * n + orientation
    digit per piece, four separate values are combined:

        corner permutation   0-23   which corner sits in each of the 4 slots, as a Lehmer rank
        corner orientation   0-80   which of its 3 stickers is yellow, per corner (base 3)
        edge permutation     0-23   which edge sits in each of the 4 slots, as a Lehmer rank
        edge orientation     0-15   whether each edge is flipped, per edge (base 2)

    packed as ((cornerPerm * 81 + cornerOri) * 24 + edgePerm) * 16 + edgeOri, so the index runs to
    24 * 81 * 24 * 16 = 746,496. Only 62,208 of those are actually reachable, since the cube's
    global invariants (corner twists summing to 0 mod 3, edge flips to 0 mod 2, and matching
    permutation parity) rule out 11 of every 12; the rest keep the NO_MACRO sentinel.

    The layer is fully described by which piece sits in each slot and how it is oriented, so
    distinct last layers get distinct indices. Valid once the F2L is solved, which confines the
    last-layer pieces to these eight slots.

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
        keyPart, oriPart = _LL_CORNER_LUT[slot][(corners[i], corners[i + 1], corners[i + 2])]
        cornerKey += keyPart
        cornerOri += oriPart

    edges = _LL_EDGE_STICKERS(state)
    edgeKey = 0
    edgeOri = 0
    for slot in range(4):
        keyPart, oriPart = _LL_EDGE_LUT[slot][(edges[slot * 2], edges[slot * 2 + 1])]
        edgeKey += keyPart
        edgeOri += oriPart

    return ((_RANK4[cornerKey] * 81 + cornerOri) * 24 + _RANK4[edgeKey]) * 16 + edgeOri


def _cachedEncode():
    """Returns an encodeLastLayer that caches its answers, for use while building the tables.

    Every state the build reaches is produced by applying strictly F2L-neutral macros to the solved
    cube, so all of them have a solved F2L - and there the 20 gathered last-layer stickers are a
    bijection with the encode index (the same fact the solver's path lookup rests on). So the
    stickers are a sound cache key, the cache is bounded by the 62,208 reachable states, and it
    returns exactly what encodeLastLayer would. The build re-encodes each state many times over, so
    this replaces most of the encodes with one gather and a dict lookup.

    Returns:
        A function taking a state and returning its encoded last-layer index.
    """
    cache = {}

    def encode(state: str) -> int:
        key = LAST_LAYER_KEY(state)
        index = cache.get(key)
        if index is None:
            index = encodeLastLayer(state)
            cache[key] = index
        return index

    return encode


def buildTable():
    """Builds the last-layer macro table, solving the layer in as few moves as the macros allow.

    Returns:
        array: The macro table of length TABLE_SIZE.
    """
    return buildStageTable(SOLVED_MASK, _cachedEncode(), TABLE_SIZE, NO_MACRO, macros()[0])


def _loadTable():
    """Loads the last-layer table, or None if it hasn't been built yet."""
    try:
        with open(_TABLE_PATH, "rb") as handle:
            return loadStageTable(handle.read())
    except FileNotFoundError:
        return None


LAST_LAYER_TABLE = _loadTable()

_PATHS_PATH = os.path.join(os.path.dirname(__file__), "data", "last_layer_paths.bin")


def buildPaths(table=None) -> dict:
    """Builds the full solution table, mapping every last layer state to the solution for it.

    The table is keyed by the 20 sticker gather tuple rather than the encode index, so that the
    solver can look a state up straight from its stickers with no encode step.

    Args:
        table (array, optional): The macro table to follow. Built if not given.

    Returns:
        dict: Maps each state's sticker tuple to its permutation and move labels.
    """
    if table is None:
        table = buildTable()
    stageMacros, inverseMacros = macros()
    return buildPathTable(SOLVED_MASK, _cachedEncode(), table, NO_MACRO, stageMacros, applyMoves,
                          lambda macro: inverseMacros[macro], keyFn=LAST_LAYER_KEY)


def _loadPaths() -> dict:
    """Loads the packed last-layer paths, or an empty dict if the file is missing.

    What comes back maps each sticker key straight to its move labels - the stage's solutions carry
    no permutation, since finishing the last layer finishes the cube.
    """
    try:
        with open(_PATHS_PATH, "rb") as handle:
            return deserialiseKeyedPaths(handle.read(), _LL_KEY_LENGTH)
    except FileNotFoundError:
        return {}


LAST_LAYER_PATHS = _loadPaths()


if __name__ == "__main__":
    generated = buildTable()
    reachable = sum(1 for b in generated if b != NO_MACRO) + 1  # + the solved state (kept NO_MACRO)
    assert reachable == 62208, f"expected 62208 reachable states, got {reachable}"
    os.makedirs(os.path.dirname(_TABLE_PATH), exist_ok=True)
    with open(_TABLE_PATH, "wb") as handle:
        handle.write(generated.tobytes())
    print(f"wrote {_TABLE_PATH} ({len(generated)} states, {reachable} reachable, {len(macros()[0])} macros)")

    paths = buildPaths(generated)
    with open(_PATHS_PATH, "wb") as handle:
        handle.write(serialiseKeyedPaths(paths))
    print(f"wrote {_PATHS_PATH} ({len(paths)} states)")
