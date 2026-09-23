"""Checks a cube state is one a real cube can be in, so a misscan gets caught before it reaches the
solver (which just returns no moves for an impossible cube)."""

from collections import Counter

from .constants import SOLVED_MASK
from .cross_table import EDGES

CENTRES = [4, 13, 22, 31, 40, 49]

# corner stickers starting from the one on the white/yellow face, all going round the same way.
# corner_table.CORNERS lists them in index order, which doesn't, and the twist sum only holds if they
# do. found by trying the 2^8 orderings against random scrambles - the only other one is the mirror
CORNER_ORDER = [
    (0, 9, 38),
    (2, 36, 29),
    (6, 18, 11),
    (8, 27, 20),
    (51, 44, 15),
    (45, 17, 24),
    (47, 26, 33),
    (53, 35, 42),
]

_UD = set(range(0, 9)) | set(range(45, 54))
_GB = set(range(9, 18)) | set(range(27, 36))

# each edge as (reference sticker, other): the white/yellow sticker if the slot has one, else green/blue
EDGE_ORDER = [(a, b) if a in _UD or (b not in _UD and a in _GB) else (b, a) for a, b in EDGES]

_CORNER_HOME = {frozenset(SOLVED_MASK[p] for p in c): i for i, c in enumerate(CORNER_ORDER)}
_EDGE_HOME = {frozenset(SOLVED_MASK[p] for p in e): i for i, e in enumerate(EDGE_ORDER)}


def _parity(permutation: list[int]) -> int:
    """0 for an even permutation, 1 for odd."""
    seen = [False] * len(permutation)
    swaps = 0
    for start in range(len(permutation)):
        length = 0
        i = start
        while not seen[i]:
            seen[i] = True
            i = permutation[i]
            length += 1
        if length:
            swaps += length - 1
    return swaps % 2


def _pieces(state: str, slots: list[tuple[int, ...]], home: dict, kind: str) -> tuple[list[int], list[str]]:
    """Where each slot's piece belongs, plus a problem for any piece that doesn't exist or appears twice."""
    problems = []
    permutation = []
    for slot in slots:
        colours = "/".join(state[p] for p in slot)
        piece = home.get(frozenset(state[p] for p in slot))
        if piece is None or len(set(colours.split("/"))) != len(slot):
            problems.append(f"there's a {kind} reading {colours}, which isn't a real piece")
        elif piece in permutation:
            problems.append(f"two {kind}s both read {colours}")
        else:
            permutation.append(piece)
    return permutation, problems


def validateCube(state: str) -> list[str]:
    """Checks a 54 sticker state could come from a real, solvable cube.

    Args:
        state (str): The cube state, in the same layout as Cube.state.

    Returns:
        list[str]: What's wrong with it, empty if nothing is.
    """
    if len(state) != 54:
        return [f"expected 54 stickers, got {len(state)}"]

    counts = Counter(state)
    wrong = [f"{counts.get(c, 0)} {c}" for c in "WGRBOY" if counts.get(c, 0) != 9]
    if wrong or len(counts) != 6:
        return ["every colour should appear 9 times, got " + ", ".join(wrong or sorted(counts))]

    if "".join(state[i] for i in CENTRES) != "".join(SOLVED_MASK[i] for i in CENTRES):
        return ["the centre stickers aren't where they should be - a face was read as the wrong one"]

    cornerPerm, problems = _pieces(state, CORNER_ORDER, _CORNER_HOME, "corner")
    edgePerm, edgeProblems = _pieces(state, EDGE_ORDER, _EDGE_HOME, "edge")
    problems += edgeProblems
    # twist, flip and parity only mean anything once every piece is a real one
    if problems:
        return problems

    twist = sum(next(i for i, p in enumerate(c) if state[p] in "WY") for c in CORNER_ORDER) % 3
    if twist:
        problems.append("a corner is twisted in place - usually one misread sticker, or a face scanned rotated")

    flip = 0
    for ref, other in EDGE_ORDER:
        key = "WY" if {state[ref], state[other]} & {"W", "Y"} else "GB"
        flip += state[ref] not in key
    if flip % 2:
        problems.append("an edge is flipped in place - usually one misread sticker, or a face scanned rotated")

    if _parity(cornerPerm) != _parity(edgePerm):
        problems.append("two pieces are swapped - usually a face scanned rotated")
    return problems
