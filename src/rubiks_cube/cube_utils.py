import operator
import struct
from collections import deque

from .constants import STRING_ROTATION_MAPPINGS

# precompute one itemgetter per rotation: itemgetter(*mapping)(mask) pulls all 54 permuted
# squares in a single C-level call, which is markedly faster than a Python-level comprehension
_ROTATION_GETTERS = {rotation: operator.itemgetter(*mapping) for rotation, mapping in STRING_ROTATION_MAPPINGS.items()}


# these functions perform operations on the masks not the cube
# this is because it is more efficient to manipulate the mask directly than the cube
# especially during the recursive BFS
def rotate(mask: str, rotation: str) -> str:
    """Rotates a mask given a specific rotation.

    Args:
        mask (str): The mask to rotate.
        rotation (str): The rotation to perform.

    Returns:
        str: The rotated mask.
    """
    return "".join(_ROTATION_GETTERS[rotation](mask))


# cache of the non-dot positions of each mask, so a mask is only scanned once
# and repeated checks (the vast majority) iterate only the squares that matter
_sparseMaskCache: dict[str, tuple[tuple[int, str], ...]] = {}


def _sparseMask(mask: str) -> tuple[tuple[int, str], ...]:
    """Returns the (index, expected character) pairs for a mask's non-dot squares.

    The result is cached, as the same masks are checked many times during solving.

    Args:
        mask (str): The mask to decompose.

    Returns:
        tuple[tuple[int, str], ...]: The non-dot (index, character) pairs.
    """
    sparse = _sparseMaskCache.get(mask)
    if sparse is None:
        sparse = tuple((i, c) for i, c in enumerate(mask) if c != ".")
        _sparseMaskCache[mask] = sparse
    return sparse


def checkMask(mask: str, state: str) -> bool:
    """Checks if a mask and a state match.

    Args:
        mask (str): The mask to check.
        state (str): The state to check against.

    Returns:
        bool: True if the mask matches the state, False otherwise.
    """
    for i, c in _sparseMask(mask):
        if state[i] != c:
            return False
    return True


def sparsifyMasks(masks) -> list[tuple[tuple[int, str], ...]]:
    """Decomposes a collection of masks into their non-dot (index, character) pairs.

    Precomputing this once lets a repeated search test many states against the same masks
    without re-looking-up each mask's sparse form on every check.

    Args:
        masks: An iterable of mask strings.

    Returns:
        list[tuple[tuple[int, str], ...]]: The sparse form of each mask.
    """
    return [_sparseMask(mask) for mask in masks]


def matchesAnySparse(sparseMasks: list[tuple[tuple[int, str], ...]], state: str) -> bool:
    """Checks whether a state matches any of the given pre-decomposed masks.

    Args:
        sparseMasks (list): Masks already decomposed by sparsifyMasks.
        state (str): The state to check against.

    Returns:
        bool: True if the state matches at least one mask, False otherwise.
    """
    for sparse in sparseMasks:
        for i, c in sparse:
            if state[i] != c:
                break
        else:
            return True
    return False


def combineMasks(mask1: str, mask2: str) -> str:
    """Combines two masks. If they both specify a certain square differently,
    priority will be given to mask1, and the output mask will take the value
    mask1 assigns to that square.

    Args:
        mask1 (str): The first mask to combine.
        mask2 (str): The second mask to combine.

    Returns:
        str: The combined mask.
    """
    # start from mask2, then overlay only mask1's specified (non-dot) squares - typically a
    # handful - instead of rebuilding all 54 characters one concatenation at a time
    out = list(mask2)
    for i, c in _sparseMask(mask1):
        out[i] = c

    return "".join(out)


def optimiseMoves(moves: list[str]) -> list[str]:
    """
    Looks through a list of moves and applies general rules to reduce the
    total number of rotations while maintaining the same output. i.e. running
    this function will result in a shorter list of moves that will perform
    the same transformation on the cube.

    Args:
        moves (list[str]): The list of moves to optimise.

    Returns:
        list[str]: The optimised list of moves.
    """
    ## checking if there is a repeated section of 4
    newList = []
    i = 0
    while i <= len(moves) - 4:
        if moves[i] == moves[i + 1] == moves[i + 2] == moves[i + 3]:
            i += 4
        else:
            newList.append(moves[i])
            i += 1

    newList += moves[i:]

    ## replacing repeated sections of length 3
    moves = newList.copy()
    newList = []
    i = 0
    while i <= len(moves) - 3:
        if moves[i] == moves[i + 1] == moves[i + 2]:
            if len(moves[i]) == 1:
                newList.append(moves[i] + "i")
            else:
                newList.append(moves[i][0])
            i += 3

        else:
            newList.append(moves[i])
            i += 1

    newList += moves[i:]

    ## removing all occurences of a move followed by its inverse

    moves = newList.copy()
    newList = []
    i = 0
    while i < len(moves) - 1:
        if moves[i][0] == moves[i + 1][0] and moves[i] != moves[i + 1]:
            i += 2
        else:
            newList.append(moves[i])
            i += 1
    # append whatever tail is left (the last move when it wasn't consumed as part of an inverse pair)
    newList += moves[i:]

    return newList


# Full-solution ("path") tables: for each reachable state of a stage, the whole solution stored as
# one 54-square permutation plus its move labels, so a stage is solved in a single lookup.

# a probe "cube" of 54 distinct characters, used to read a move sequence off as a permutation
_PATH_PROBE = "".join(chr(33 + i) for i in range(54))

# the 12 possible recorded move labels, in a fixed order; the index is the on-disk code for the label
MOVE_LABELS = [face + direction for face in "UDFBLR" for direction in ("", "i")]
_LABEL_TO_CODE = {label: code for code, label in enumerate(MOVE_LABELS)}


def _parseMoves(sequence: str):
    """Yields the rotation to apply and the label to record for each move in a sequence.

    Moves are parsed exactly as executeSequence parses them: a trailing ' or i means the move is
    anticlockwise, and its label gets an i.

    Args:
        sequence (str): The sequence of moves to parse.

    Yields:
        tuple[str, str]: The rotation and the recorded label for each move.
    """
    i = 0
    n = len(sequence)
    while i < n:
        ch = sequence[i]
        if ch not in "UDFBLR":
            i += 1
            continue
        if i + 1 < n and sequence[i + 1] in ("'", "i"):
            yield ch + "'", ch + "i"
            i += 2
        else:
            yield ch, ch
            i += 1


def applySequence(state: str, sequence: str) -> str:
    """Applies a sequence of moves to a state, parsed the same way executeSequence parses it.

    Args:
        state (str): The state to apply the moves to.
        sequence (str): The sequence of moves to apply.

    Returns:
        str: The state after the moves have been applied.
    """
    for rotation, _ in _parseMoves(sequence):
        state = rotate(state, rotation)
    return state


def compileSequence(sequence: str) -> tuple[tuple[int, ...], tuple[str, ...]]:
    """Compiles a sequence of moves into a single permutation and the labels to record for it.

    The permutation is the whole sequence composed into one 54 square gather, so that
    result[i] = state[permutation[i]]. The labels are what executeSequence would append to
    movesMade. Both are read off the distinct label probe, so applying the permutation has the same
    effect on any state as applying the moves one at a time.

    Args:
        sequence (str): The sequence of moves to compile.

    Returns:
        tuple[tuple[int, ...], tuple[str, ...]]: The composed permutation and the move labels.
    """
    state = _PATH_PROBE
    labels = []
    for rotation, label in _parseMoves(sequence):
        state = rotate(state, rotation)
        labels.append(label)
    return tuple(ord(c) - 33 for c in state), tuple(labels)


def buildPathTable(solvedState, encodeFn, table, sentinel, generators, applyGen, stepString,
                   keyFn=None) -> dict:
    """Builds a stage's full-solution table from its (already-proven) single-step table.

    Enumerates every reachable state by BFS over generators, then for each state follows
    table to solved exactly as the current solver does - so the produced solution (permutation +
    labels) is identical to today's move-by-move output.

    Args:
        solvedState (str): The solved cube string.
        encodeFn: The stage's encode function (state -> index).
        table: The stage's single-step move/macro table.
        sentinel: The table's "already solved" value.
        generators: The forward generators used to reach every state (moves or macros).
        applyGen: applyGen(state, generator) -> state.
        stepString: stepString(table_value) -> move string that steps a state towards solved.
        keyFn: Optional keyFn(state) -> hashable used as each entry's key instead of its encode
            index. Only valid when it is a bijection with the index over reachable states (so no two
            states collide onto one key); this lets the solver look a stage up straight from the
            gathered stickers without computing the index. Defaults to keying by index.

    Returns:
        dict: key -> (permutation, labels) for every reachable non-solved state (key is the
        encode index, or keyFn(state) when given).
    """
    solvedIdx = encodeFn(solvedState)
    seen = {solvedIdx}
    reps = {solvedIdx: solvedState}
    queue = deque([solvedIdx])
    while queue:
        state = reps[queue.popleft()]
        for generator in generators:
            newState = applyGen(state, generator)
            newIdx = encodeFn(newState)
            if newIdx not in seen:
                seen.add(newIdx)
                reps[newIdx] = newState
                queue.append(newIdx)

    paths = {}
    for idx, state in reps.items():
        parts = []
        s = state
        j = idx
        while table[j] != sentinel:
            step = stepString(table[j])
            parts.append(step)
            s = applySequence(s, step)
            j = encodeFn(s)
        if parts:  # everything but the already-solved state
            paths[idx if keyFn is None else keyFn(state)] = compileSequence("".join(parts))
    return paths


def serialisePaths(paths: dict) -> bytes:
    """Packs a path table into bytes, one record per entry.

    Each record holds a uint32 index, a 54 byte permutation, a label count, and that many label
    codes.

    Args:
        paths (dict): The path table to pack.

    Returns:
        bytes: The packed path table.
    """
    buf = bytearray()
    for idx, (permutation, labels) in paths.items():
        buf += struct.pack("<I", idx)
        buf += bytes(permutation)
        buf.append(len(labels))
        buf += bytes(_LABEL_TO_CODE[label] for label in labels)
    return bytes(buf)


def deserialisePaths(data: bytes) -> dict:
    """Loads a packed path table.

    The permutation is kept as a tuple of ints rather than bytes, so that itemgetter can unpack it
    directly when solving instead of boxing 54 ints out of a bytes object on every call.

    Args:
        data (bytes): The packed path table.

    Returns:
        dict: Maps each index to its permutation and the labels of the moves solving it.
    """
    paths = {}
    pos = 0
    n = len(data)
    while pos < n:
        idx = struct.unpack_from("<I", data, pos)[0]
        pos += 4
        permutation = tuple(data[pos:pos + 54])
        pos += 54
        count = data[pos]
        pos += 1
        labels = tuple(MOVE_LABELS[code] for code in data[pos:pos + count])
        pos += count
        paths[idx] = (permutation, labels)
    return paths


def serialiseKeyedPaths(paths: dict) -> bytes:
    """Packs a path table keyed by sticker tuples into bytes, one record per entry.

    Each record holds the key's stickers, a 54 byte permutation, a label count, and that many label
    codes. Every key must be the same length, so that the fixed size records parse back cleanly.

    Args:
        paths (dict): The path table to pack, keyed by tuples of single character colours.

    Returns:
        bytes: The packed path table.
    """
    buf = bytearray()
    for key, (permutation, labels) in paths.items():
        buf += bytes(ord(c) for c in key)
        buf += bytes(permutation)
        buf.append(len(labels))
        buf += bytes(_LABEL_TO_CODE[label] for label in labels)
    return bytes(buf)


def deserialiseKeyedPaths(data: bytes, keyLength: int) -> dict:
    """Loads a table packed by serialiseKeyedPaths.

    Each key is decoded back to a tuple of single character strings, so that it matches the tuple a
    stage's sticker gather produces when looking a state up.

    Args:
        data (bytes): The packed path table.
        keyLength (int): The number of stickers making up each key.

    Returns:
        dict: Maps each key to its permutation and the labels of the moves solving it.
    """
    paths = {}
    pos = 0
    n = len(data)
    while pos < n:
        key = tuple(chr(b) for b in data[pos:pos + keyLength])
        pos += keyLength
        permutation = tuple(data[pos:pos + 54])
        pos += 54
        count = data[pos]
        pos += 1
        labels = tuple(MOVE_LABELS[code] for code in data[pos:pos + count])
        pos += count
        paths[key] = (permutation, labels)
    return paths


def printAnalysis(analysis: dict) -> None:
    """Prints the analysis of multiple solves to the console.

    Args:
        analysis (dict): The analysis dictionary containing the statistics.
    """

    print("\n-----------------------------")
    print(f"Average Solve Time: {analysis['avg_time']:.2g}")
    print(f"Avg number of Rotations: {round(analysis['avg_moves'], 5)}")
    print(f"Avg number of optimised rotations: {round(analysis['avg_moves_optimised'], 5)}")
    print(f"Avg number of rotations saved:  {round(analysis['avg_moves_saved'],2)}")

    print("-----------------------------")

    print(f"Avg Cross Time: {analysis['avg_cross_time']:.2g}")
    print(f"Avg Corners Time: {analysis['avg_corners_time']:.2g}")
    print(f"Avg Middles Time: {analysis['avg_middles_time']:.2g}")
    print(f"Avg Last Layer Time: {analysis['avg_last_layer_time']:.2g}")

    print("-----------------------------")

    print(f"Max Cross Time: {analysis['max_cross_time']:.2g}")
    print(f"Max Corners Time: {analysis['max_corners_time']:.2g}")
    print(f"Max Middles Time: {analysis['max_middles_time']:.2g}")
    print(f"Max Last Layer Time: {analysis['max_last_layer_time']:.2g}")
    print("-----------------------------")
