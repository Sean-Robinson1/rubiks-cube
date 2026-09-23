"""Enumerates the macro set a stage's table search runs over.

A stage may only use move sequences that leave the earlier stages' pieces exactly where they were -
the corner stage must not disturb the cross, the middle stage neither cross nor corners, the last
layer neither. Those macros used to be written out by hand, a dozen or so per stage, which is why a
stage's solutions ran far longer than they needed to: the search can only be as good as the moves it
is given.

The constraint is on the sequence as a whole, not on the states it passes through, so a macro is
free to break the earlier stages mid-sequence as long as it puts everything back - which is exactly
what hand-written cube algorithms do. Enumerating every such sequence up to length 8 directly would
mean walking ~2.3e8 move sequences, so they are found by meeting in the middle instead. Applying A
then B gives a permutation of perm[i] = permA[permB[i]], so

    A then B fixes position i  <=>  permB[i] == invert(permA)[i]

Keying each half-sequence by its permutation restricted to the preserved positions - the inverse for
the left half, the forward one for the right - turns "every neutral sequence up to length 2h" into a
join between two buckets of half-sequences of length h.

The results are then deduplicated by their effect on the stage's tracked pieces, keeping the
shortest sequence for each. That cap is what keeps the set usable: a stage has only so many distinct
effects, so enumerating deeper finds shorter macros rather than endlessly more of them.
"""

from collections import defaultdict

from .constants import POSSIBLE_ROTATIONS
from .cube_utils import composeMoves

_IDENTITY = tuple(range(54))
_MOVE_PERMUTATIONS = {move: composeMoves([move]) for move in POSSIBLE_ROTATIONS}


def _compose(left: tuple, right: tuple) -> tuple:
    """Composes two permutations into the one applying left and then right.

    Args:
        left (tuple): The permutation applied first.
        right (tuple): The permutation applied second.

    Returns:
        tuple: The composed 54 square permutation.
    """
    return tuple(left[i] for i in right)


def _invert(permutation: tuple) -> tuple:
    """Returns the permutation undoing the given one.

    Args:
        permutation (tuple): The permutation to invert.

    Returns:
        tuple: The inverse permutation.
    """
    inverse = [0] * 54
    for position, source in enumerate(permutation):
        inverse[source] = position
    return tuple(inverse)


def _halfSequences(maxLength: int) -> list:
    """Builds every move sequence up to maxLength, paired with its permutation.

    Sequences turning the same face twice in a row are skipped, since some shorter sequence has the
    same effect.

    Args:
        maxLength (int): The longest sequence to generate.

    Returns:
        list: The (permutation, moves) pair for each sequence, including the empty one.
    """
    sequences: list[tuple[tuple[int, ...], tuple[str, ...]]] = [(_IDENTITY, ())]
    frontier = [(_IDENTITY, ())]
    for _ in range(maxLength):
        nextFrontier = []
        for permutation, moves in frontier:
            for move in POSSIBLE_ROTATIONS:
                if moves and moves[-1][0] == move[0]:
                    continue
                grown = (_compose(permutation, _MOVE_PERMUTATIONS[move]), moves + (move,))
                nextFrontier.append(grown)
                sequences.append(grown)
        frontier = nextFrontier
    return sequences


def enumerateMacros(preserved, tracked, halfDepth: int = 4, maxLength: int | None = None) -> list:
    """Finds the shortest preservation-respecting macro for each distinct effect on a stage.

    Args:
        preserved: The sticker positions a macro must leave exactly where it found them.
        tracked: The sticker positions whose arrangement decides a macro's effect. This must cover
            every slot the stage's pieces can occupy, not just their solved slots, since a macro
            permutes slots regardless of what happens to be sitting in them.
        halfDepth (int): The longest half-sequence to enumerate; macros run to twice this.
        maxLength (int, optional): Discards any macro longer than this. Useful where the enumeration
            finds far more macros than a stage's search can afford to branch over.

    Returns:
        list: The macros, each a list of moves, ordered shortest first so the set is identical from
        one run to the next (the table stores macro indices, so the order has to be stable).
    """
    halves = _halfSequences(halfDepth)

    byForward = defaultdict(list)
    for permutation, moves in halves:
        byForward[tuple(permutation[i] for i in preserved)].append((permutation, moves))

    trackedIdentity = tuple(tracked)
    shortest = {}
    for permutation, moves in halves:
        inverse = _invert(permutation)
        for rightPermutation, rightMoves in byForward.get(tuple(inverse[i] for i in preserved), ()):
            combined = moves + rightMoves
            if maxLength is not None and len(combined) > maxLength:
                continue
            effect = tuple(_compose(permutation, rightPermutation)[i] for i in tracked)
            if effect == trackedIdentity:
                continue  # leaves the stage's own pieces alone, so it is no use to the search
            previous = shortest.get(effect)
            if previous is None or len(combined) < len(previous):
                shortest[effect] = combined

    return [list(moves) for moves in sorted(shortest.values(), key=lambda m: (len(m), m))]
