import array
import heapq
import itertools
import operator
import struct
from collections import deque

from .constants import STRING_ROTATION_MAPPINGS

# every rotation is a fixed reshuffle of the 54 squares: mapping[i] is the square of the old state
# that ends up at position i, so rotating is just result[i] = mask[mapping[i]]. operator.itemgetter
# bakes a list of indices into a reusable callable that looks them all up at once and hands back a
# tuple - itemgetter(2, 0, 1)("abc") "abc" gives ("c", "a", "b"). Building one per rotation up
# front means rotate() fetches all 54 squares in a single C-level call and joins the tuple back
# into a string, rather than indexing the mask 54 times in Python on every move.
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


def applyMoves(state: str, moves) -> str:
    """Applies a list of already-split moves to a state.

    Args:
        state (str): The state to apply the moves to.
        moves: An iterable of rotations, e.g. ["R", "D'", "R'"].

    Returns:
        str: The state after the moves have been applied.
    """
    for move in moves:
        state = rotate(state, move)
    return state


def invertMove(move: str) -> str:
    """Returns the move that undoes a single move.

    Args:
        move (str): The move to invert.

    Returns:
        str: The inverted move.
    """
    return move[0] if move.endswith("'") else move + "'"


# cache of the non-dot positions of each mask, so a mask is only scanned once
# and repeated checks (the vast majority) iterate only the squares that matter
_sparseMaskCache: dict[str, tuple[tuple[int, str], ...]] = {}


def _sparseMask(mask: str) -> tuple[tuple[int, str], ...]:
    """Returns the (index, expected character) pairs for a mask's non-dot squares.

    I used to write masks as "WW...BGR ...", with dots being wildcards. That stores a load of
    information I don't care about, so now I keep the index of each facelet I do care about
    and its expected colour, and only check those.

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
    """Decomposes a collection of masks into their sparse (index, character) pairs.

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


# opposite faces turn disjoint layers, so their moves commute and can be reordered freely
_OPPOSITE_FACE = {"U": "D", "D": "U", "F": "B", "B": "F", "L": "R", "R": "L"}


def optimiseMoves(moves: list[str]) -> list[str]:
    """Reduces a move list to a shorter one with the same net effect on the cube.

    The list is folded into a stack of [face, net] runs, net being that face's clockwise
    quarter-turns mod 4. A run reaching a full turn is dropped, which re-exposes the run beneath
    it. Opposite faces commute, so a move can also join its own run through a single run of the
    opposite face, which reduces R L Ri to L.

    Args:
        moves (list[str]): The moves to optimise, each a face UDFBLR with an optional trailing
            i for anticlockwise.

    Returns:
        list[str]: The reduced moves, never longer than the input. A 180-degree turn is written as
        two quarter-turns, as there is no double-turn label.
    """
    stack: list[list] = []  # [face, net] runs, net in {1, 2, 3}; adjacent runs have different faces
    for move in moves:
        face = move[0]
        turn = 3 if move.endswith("i") else 1  # anticlockwise is -1, i.e. 3 clockwise turns (mod 4)

        # this move's own run is either on top, or one below a run of the opposite face
        if stack and stack[-1][0] == face:
            index = len(stack) - 1
        elif len(stack) > 1 and stack[-1][0] == _OPPOSITE_FACE[face] and stack[-2][0] == face:
            index = len(stack) - 2
        else:
            stack.append([face, turn])
            continue

        stack[index][1] = (stack[index][1] + turn) % 4
        if stack[index][1] == 0:  # a whole turn - this run is now the identity, so drop it
            del stack[index]

    reduced = []
    for face, net in stack:
        if net == 1:
            reduced.append(face)
        elif net == 3:
            reduced.append(face + "i")
        else:  # a 180-degree turn
            reduced.append(face)
            reduced.append(face)
    return reduced


def buildGroupLUT(slotLUT: list, slotKeys, groupSize: int = 2) -> list:
    """Merges adjacent per-slot contribution tables into wider-key lookup tables.

    An encode index built as a sum of independent per-slot contributions (each already folded to
    include its place value) can be computed with fewer, wider dictionary lookups: the combined
    contribution of a group of ``groupSize`` adjacent slots is precomputed once, keyed by the
    concatenation of those slots' stickers. The encode then does one lookup per group instead of one
    per slot, with no Python loop, for the identical index.

    ``slotKeys`` must be the *exhaustive* set of sticker tuples a single slot can show, so every key a
    real state can produce is present in the result; a slot holding an untracked piece is simply
    absent from ``slotLUT`` and contributes 0, exactly as the per-slot encode skipped it.

    Args:
        slotLUT (list): One dict per slot, mapping that slot's sticker tuple to its contribution.
        slotKeys: The exhaustive set of sticker tuples any one slot can display.
        groupSize (int): How many adjacent slots to merge per group (default 2; must divide the slot count).

    Returns:
        list: One combined-contribution dict per group, keyed by the group's concatenated stickers.
    """
    groups = []
    for start in range(0, len(slotLUT), groupSize):
        members = slotLUT[start:start + groupSize]
        combined = {}
        for combo in itertools.product(slotKeys, repeat=len(members)):
            key = tuple(itertools.chain.from_iterable(combo))
            combined[key] = sum(members[i].get(combo[i], 0) for i in range(len(members)))
        groups.append(combined)
    return groups


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


def composeMoves(moves) -> tuple[int, ...]:
    """Composes a list of moves into the single permutation that applies all of them at once.

    Read off the distinct label probe, so permutation[i] is the square of the old state that ends up
    at position i - the same form compileSequence produces for whole solutions. Applying a composed
    macro is one gather rather than one rotate per move in it.

    Args:
        moves: An iterable of rotations, e.g. ["R", "D'", "R'"].

    Returns:
        tuple[int, ...]: The composed 54 square permutation.
    """
    return tuple(ord(c) - 33 for c in applyMoves(_PATH_PROBE, moves))


def loadStageTable(data: bytes):
    """Reads back a stage table written by buildStageTable.

    Args:
        data (bytes): The table as written to disk.

    Returns:
        array: The table, one 16 bit macro index per state.
    """
    table = array.array("H")
    table.frombytes(data)
    return table


def buildStageTable(solvedState, encodeFn, tableSize, sentinel, macros):
    """Builds a stage's single-step table by move-weighted (Dijkstra) search backwards from solved.

    Each macro edge is weighted by its move count, so every reachable state ends up storing a macro
    on a move-shortest path to solved, solving the stage in as few moves as the macro set allows
    rather than in the fewest macros. The solved state and unreachable indices keep the sentinel.

    Every macro is composed into one permutation up front, so relaxing an edge is a single gather
    instead of a rotate per move - the search visits each (state, macro) pair exactly once, so that
    composition is the whole cost of the build.

    The table stores a macro index per state as 16 bits, since an enumerated macro set runs to
    hundreds of entries - well past what the byte-wide tables held when the macros were written by
    hand.

    Args:
        solvedState (str): The solved cube string.
        encodeFn: The stage's encode function (state -> index).
        tableSize (int): The number of encodable states.
        sentinel (int): The value left at the solved state and at any unreachable index. It has to
            be outside the range of macro indices.
        macros (list): The stage's macros, each a list of moves.

    Returns:
        array: The stage's table, of length tableSize.
    """
    if len(macros) >= sentinel:
        raise ValueError(f"{len(macros)} macros cannot be indexed below the sentinel {sentinel}")

    getters = [operator.itemgetter(*composeMoves(macro)) for macro in macros]
    weights = [len(macro) for macro in macros]

    table = array.array("H", [sentinel]) * tableSize
    distance = [1 << 30] * tableSize

    solvedIdx = encodeFn(solvedState)
    distance[solvedIdx] = 0
    reps = {solvedIdx: solvedState}
    queue = [(0, solvedIdx)]

    while queue:
        dist, idx = heapq.heappop(queue)
        if dist > distance[idx]:
            continue  # stale heap entry
        state = reps[idx]
        for macro, getter in enumerate(getters):
            newState = "".join(getter(state))
            newIdx = encodeFn(newState)
            newDistance = dist + weights[macro]
            if newDistance < distance[newIdx]:
                # stepping back towards solved applies the macro's inverse, so store the macro
                # index and look it up in the stage's INVERSE_MACROS when solving
                distance[newIdx] = newDistance
                table[newIdx] = macro
                reps[newIdx] = newState
                heapq.heappush(queue, (newDistance, newIdx))

    return table


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
    # the enumeration below applies every generator to every reachable state, so a multi-move
    # generator is composed into a single permutation first, on the same reasoning as the steps below
    genGetters = []
    for generator in generators:
        moves = [generator] if isinstance(generator, str) else list(generator)
        genGetters.append(operator.itemgetter(*composeMoves(moves)) if len(moves) > 1 else None)

    solvedIdx = encodeFn(solvedState)
    seen = {solvedIdx}
    reps = {solvedIdx: solvedState}
    queue = deque([solvedIdx])
    while queue:
        state = reps[queue.popleft()]
        for generator, getter in zip(generators, genGetters):
            newState = "".join(getter(state)) if getter is not None else applyGen(state, generator)
            newIdx = encodeFn(newState)
            if newIdx not in seen:
                seen.add(newIdx)
                reps[newIdx] = newState
                queue.append(newIdx)

    # A stage has only as many distinct steps as it has generators, and every state's walk applies
    # them over and over, so each multi-move step is composed into one permutation up front - one
    # gather in place of a rotate per move. A single-move step is already exactly one gather, so
    # composing it would only add a lookup; those keep going through applySequence.
    stepGetters = {}
    for value in set(table):
        if value == sentinel:
            continue
        step = stepString(value)
        permutation, labels = compileSequence(step)
        if len(labels) > 1:
            stepGetters[step] = operator.itemgetter(*permutation)

    paths = {}
    for idx, state in reps.items():
        parts = []
        s = state
        j = idx
        while table[j] != sentinel:
            step = stepString(table[j])
            parts.append(step)
            getter = stepGetters.get(step)
            s = "".join(getter(s)) if getter is not None else applySequence(s, step)
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
