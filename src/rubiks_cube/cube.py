import copy
import logging
import operator
import random
import time

from .constants import *
from .corner_table import CORNER_TABLE, INVERSE_MACROS, NO_MACRO, encodeCorners
from .cross_table import CROSS_TABLE, NO_MOVE, encodeCross
from .middle_table import INVERSE_MACROS as MIDDLE_INVERSE_MACROS
from .middle_table import MIDDLE_TABLE
from .middle_table import NO_MACRO as NO_MIDDLE_MACRO
from .middle_table import encodeMiddles
from .last_layer_table import INVERSE_MACROS as LL_INVERSE_MACROS
from .last_layer_table import LAST_LAYER_TABLE
from .last_layer_table import NO_MACRO as NO_LL_MACRO
from .last_layer_table import encodeLastLayer
from .cube_utils import checkMask, optimiseMoves, printAnalysis, rotate


class Cube:
    def __init__(self, startStr: str = None) -> None:
        """Initialises a Cube object.

        Args:
            startStr (str, optional): A string of length 54 representing the cube's state.
                                      If None, the cube is initialised in a solved state.
                                      Defaults to None.
        """
        # the cube's state is a single 54 character string (6 faces, 9 squares each, in
        # face-major, row-major order). This is the same representation used for pathfinding,
        # so moves are applied directly to it and no conversion is needed to search or hash.
        self.state: str = SOLVED_MASK
        self.initialiseFaces(startStr)
        self.calculateFaces("R", "W")

        self.movesMade = []

    def __str__(self) -> str:
        return self.state

    def __repr__(self) -> str:
        return f"Cube('{str(self)}')"

    def __getitem__(self, index: int) -> list[list[str]]:
        return self.faces[index]

    def __hash__(self) -> int:
        return hash(self.state)

    @property
    def isSolved(self) -> bool:
        return self.state == SOLVED_MASK

    @property
    def optimisedMoves(self) -> list[str]:
        return optimiseMoves(self.movesMade)

    @property
    def faces(self) -> list[list[list[str]]]:
        """The cube's state decoded into a 6x3x3 nested list of squares.

        This is a read-only view rebuilt from state on each access; mutate the cube
        through its rotation methods, not by assigning to the returned list.
        """
        s = self.state
        return [[[s[face * 9 + row * 3 + col] for col in range(3)] for row in range(3)] for face in range(6)]

    def initialiseFaces(self, faceStr: str = None) -> None:
        """Initialises the cube's state from a string representation.

        Args:
            faceStr (str): A string of length 54 representing the cube's faces.
        """
        if faceStr:
            self.state = faceStr

    def calculateFaces(self, front: str, top: str) -> None:
        """Calculates faces relative to a chosen front face and a chosen top face.

        Note - this assumes the two faces are not opposites.

        Args:
            front (str): The colour of the front face.
            top (str): The colour of the top face.
        """
        if front == top or front == self.getOppositeFace(top):
            logging.critical("Front and top faces cannot be the same or opposites.")
            raise ValueError("Front and top faces cannot be the same or opposites.")
        self.top = top
        self.front = front
        self.bottom = self.getOppositeFace(top)
        self.back = self.getOppositeFace(front)

        if self.top == "W":
            self.left = self.getLeftFace(self.front)
        elif self.top == "Y":
            self.left = self.getRightFace(self.front)
        elif self.front == "W":
            self.left = self.getRightFace(self.top)
        elif self.front == "Y":
            self.left = self.getLeftFace(self.top)
        elif self.top == self.getLeftFace(self.front):
            self.left = "Y"
        else:
            self.left = "W"

        self.right = self.getOppositeFace(self.left)

        self.relativeMoveMap = {
            "R": self.right,
            "L": self.left,
            "F": self.front,
            "B": self.back,
            "U": self.top,
            "D": self.bottom,
        }

    def getPlottingList(self) -> list[str]:
        """Returns a list of colours in the correct order to be plotted.

        Returns:
            list[str]: A list of colours in the order required for plotting.
        """
        outputList = []
        faces = self.faces
        for face in [(0, -1, 1), (5, 1, 1), (2, 1, 1), (4, 1, -1), (1, 1, -1), (3, 1, 1)]:
            for row in faces[face[0]][:: face[1]]:
                for square in row[:: face[2]]:
                    outputList.append(PLOTTING_COLOUR_MAP[square])
        return outputList

    def displayCube(self, faces: list[list[str]] = None) -> None:
        """Displays the cube in the console. If no faces are provided, the current state of the cube is displayed.

        Args:
            faces (list[list[str]], optional): A 2D list representing the cube's faces. Defaults to None.
        """
        if faces is None:
            faces = self.faces

        print("\n\n")

        for row in faces[0]:
            print(10 * " ", end="")
            for square in row:
                print(COLOUR_TO_UNICODE.get(square, ERROR_CHAR), end=" ")
            print()

        print()

        for row in range(3):
            for faceIndex in range(1, 5):
                face = faces[faceIndex]

                for square in face[row]:
                    print(COLOUR_TO_UNICODE.get(square, ERROR_CHAR), end=" ")
                print(" ", end="")
            print()

        print()

        for row in faces[5]:
            print(10 * " ", end="")
            for square in row:
                print(COLOUR_TO_UNICODE.get(square, ERROR_CHAR), end=" ")
            print()

        print()

    def randomise(self) -> list[str]:
        """Randomises the cube to a valid state by performing a series of random moves.

        Returns:
            list[str]: The sequence of moves used to randomise the cube.
        """
        turns = ["R", "L", "U", "D", "F", "B"]
        sequence = []
        for _ in range(50):
            move = turns[random.randint(0, 5)]

            if random.random() > 0.5:
                move += "i"

            sequence.append(move)

        self.executeSequence("".join(sequence))
        return sequence

    def workBackwards(self, sequence: list[str]) -> None:
        """Given the sequence of moves that scrambled/randomised the cube, this
        function will work backwards and solve the cube. This method is often
        used to fake solving the cube, specifically cubes of much larger sizes.

        Args:
            sequence (list[str]): The sequence of moves that scrambled the cube.
        """
        invertedSequence = ""
        for i in range(len(sequence) - 1, -1, -1):
            turn = sequence[i]
            if len(turn) == 2:
                invertedSequence += turn[0]
            else:
                invertedSequence += turn + "i"

        self.executeSequence(invertedSequence)

    def rotateU(self, direction: bool = CLOCKWISE) -> None:
        """Performs a rotation of the upper face.

        Args:
            direction (bool, optional): The direction to rotate the face. Defaults to CLOCKWISE.
        """
        self.__applyMove("U", direction)

    def rotateD(self, direction: bool = CLOCKWISE) -> None:
        """Performs a rotation of the down face.

        Args:
            direction (bool, optional): The direction to rotate the face. Defaults to CLOCKWISE.
        """
        self.__applyMove("D", direction)

    def rotateF(self, direction: bool = CLOCKWISE) -> None:
        """Performs a rotation of the front face.

        Args:
            direction (bool, optional): The direction to rotate the face. Defaults to CLOCKWISE.
        """
        self.__applyMove("F", direction)

    def rotateB(self, direction: bool = CLOCKWISE) -> None:
        """Performs a rotation of the back face.

        Args:
            direction (bool, optional): The direction to rotate the face. Defaults to CLOCKWISE.
        """
        self.__applyMove("B", direction)

    def rotateR(self, direction: bool = CLOCKWISE) -> None:
        """Performs a rotation of the right face.

        Args:
            direction (bool, optional): The direction to rotate the face. Defaults to CLOCKWISE.
        """
        self.__applyMove("R", direction)

    def rotateL(self, direction: bool = CLOCKWISE) -> None:
        """Performs a rotation of the left face.

        Args:
            direction (bool, optional): The direction to rotate the face. Defaults to CLOCKWISE.
        """
        self.__applyMove("L", direction)

    def __applyMove(self, face: str, direction: bool = CLOCKWISE) -> None:
        """Applies a single quarter turn to the cube's state string.

        Args:
            face (str): The face to turn, in move notation (one of U, D, F, B, L, R).
            direction (bool, optional): The direction to turn the face. Defaults to CLOCKWISE.
        """
        self.state = rotate(self.state, face if direction == CLOCKWISE else face + "'")

    def executeSequence(self, sequence: str, useColours: bool = False) -> None:
        """Executes a sequence of moves on the Rubik's Cube.

        Args:
            sequence (str): A string representing the sequence of moves to execute.
            useColours (bool, optional): If True, uses colour notation (R, G, W, Y, B, O) instead of
                                         face notation (R, L, U, D, F, B). Defaults to False.
        """
        seq = sequence.replace(" ", "")

        if not useColours:
            letterToFunc = {
                "R": self.rotateR,
                "L": self.rotateL,
                "U": self.rotateU,
                "D": self.rotateD,
                "F": self.rotateF,
                "B": self.rotateB,
            }
        else:
            letterToFunc = {
                "B": self.rotateR,
                "G": self.rotateL,
                "W": self.rotateU,
                "Y": self.rotateD,
                "R": self.rotateF,
                "O": self.rotateB,
            }

        i = 0
        while i < len(seq):
            ch = seq[i]
            if ch not in letterToFunc:
                i += 1
                continue

            func = letterToFunc[ch]
            direction = CLOCKWISE
            repeats = 1
            j = i + 1

            if j < len(seq) and seq[j] in ("'", "i"):
                direction = ANTICLOCKWISE
                j += 1

            elif j < len(seq) and seq[j].isdigit():
                numStr = ""
                while j < len(seq) and seq[j].isdigit():
                    numStr += seq[j]
                    j += 1
                try:
                    repeats = max(1, int(numStr))
                except ValueError:
                    repeats = 1

            moveLabel = ch + ("i" if direction == ANTICLOCKWISE else "")
            for _ in range(repeats):
                func(direction)
                self.movesMade.append(moveLabel)

            i = j

    def checkMask(self, mask: str) -> bool:
        """Checks if the cube matches a mask pattern.

        Args:
            mask (str): A string of length 54 representing the mask pattern.

        Returns:
            bool: True if the cube matches the mask, False otherwise.
        """
        return checkMask(mask, str(self))

    def getOppositeFace(self, colour: str) -> str:
        """Returns the opposite face relative to the given face colour

        Args:
            colour (str): The colour of the face.

        Returns:
            str: The colour of the opposite face.
        """
        return OPPOSITE_FACE_MAPPING.get(colour)

    def getLeftFace(self, colour: str) -> str:
        """Returns the left face relative to the given face colour.

        Note - this assumes the white face is currently at the top.

        Args:
            colour (str): The colour of the face.

        Returns:
            str: The colour of the left face.
        """
        return LEFT_FACE_MAPPING.get(colour)

    def getRightFace(self, colour: str) -> str:
        """Returns the right face relative to the given face colour.

        Note - this assumes the white face is currently at the top.

        Args:
            colour (str): The colour of the face.

        Returns:
            str: The colour of the right face.
        """
        return RIGHT_FACE_MAPPING.get(colour)

    def getMoveRelative(self, move: str) -> str:
        """Returns the move relative to the current front and top faces.

        Args:
            move (str): A single character representing the move to convert.

        Returns:
            str: The move relative to the current front and top faces.
        """
        return self.relativeMoveMap.get(move[0], move[0]) + move[1:]

    def executeSequenceRelative(self, sequence: str) -> None:
        """Executes a sequence of moves relative to the current front and top faces.

        Args:
            sequence (str): A string representing the sequence of moves to execute.
        """
        out = ""

        for letter in sequence:
            out += self.relativeMoveMap.get(letter, letter)

        self.executeSequence(out, True)

    def convertSequenceFromFace(self, face: str, sequence: str) -> None:
        """Converts a sequence of moves from the perspective of a given face.

        Note - this assumes the white face is currently at the top and the function
        is being called on the Red, Blue, Green or Orange faces.

        Args:
            face (str): The colour of the face to convert from.
            sequence (str): A string representing the sequence of moves to convert.
        """
        out = ""
        for letter in sequence:
            out += RELATIVE_FACE_MAPPING.get(face, {}).get(letter, letter)

        self.executeSequence(out)

    def solve(self) -> None:
        """Solves the cube stage by stage, using a combination of pathfinding and
        predefined sequences to achieve the solution."""
        self.movesMade = []
        self.solveCross()
        self.solveF2LCorners()
        self.solveF2LMiddlePieces()
        self.solveLastLayer()

    def solveCross(self) -> None:
        """Solves the white cross on the top of the cube.

        Uses a precomputed table that maps every white-cross configuration to the next move on an
        optimal path to the solved cross, so the cross is solved by a short sequence of O(1) lookups
        rather than a search. Each move is applied as a precomposed permutation.
        """
        move = CROSS_TABLE[encodeCross(self.state)]
        while move != NO_MOVE:
            self.state = "".join(_CROSS_GETTERS[move](self.state))
            self.movesMade.extend(_CROSS_MOVES[move])
            move = CROSS_TABLE[encodeCross(self.state)]

    def solveF2LCorners(self) -> None:
        """Solves the four white F2L corners.

        Uses a precomputed table that maps every white-corner configuration to a cross-preserving
        macro stepping one closer to solved, so the corners are placed by a short sequence of O(1)
        lookups without disturbing the cross. Each macro is applied as a precomposed permutation.
        """
        macro = CORNER_TABLE[encodeCorners(self.state)]
        while macro != NO_MACRO:
            self.state = "".join(_CORNER_GETTERS[macro](self.state))
            self.movesMade.extend(_CORNER_MOVES[macro])
            macro = CORNER_TABLE[encodeCorners(self.state)]

    def solveF2LMiddlePieces(self) -> None:
        """Inserts the four middle-layer edges to complete the F2L.

        Uses a precomputed table that maps every middle-edge configuration to a macro that preserves
        the cross and corners while stepping one closer to solved, so the middle layer is finished by
        a sequence of O(1) lookups. Each macro is applied as a precomposed permutation.
        """
        macro = MIDDLE_TABLE[encodeMiddles(self.state)]
        while macro != NO_MIDDLE_MACRO:
            self.state = "".join(_MIDDLE_GETTERS[macro](self.state))
            self.movesMade.extend(_MIDDLE_MOVES[macro])
            macro = MIDDLE_TABLE[encodeMiddles(self.state)]

    def solveLastLayer(self) -> None:
        """Solves the entire last layer (the yellow face) in one table-driven pass.

        Uses a precomputed table that maps every last-layer configuration to a strictly F2L-neutral
        macro stepping one closer to solved, so the corners and edges of the final layer are finished
        together by a short sequence of O(1) lookups without disturbing the solved first two layers.
        Each macro is applied as a precomposed permutation.
        """
        macro = LAST_LAYER_TABLE[encodeLastLayer(self.state)]
        while macro != NO_LL_MACRO:
            self.state = "".join(_LL_GETTERS[macro](self.state))
            self.movesMade.extend(_LL_MOVES[macro])
            macro = LAST_LAYER_TABLE[encodeLastLayer(self.state)]

    def showMask(self, mask: str) -> None:
        """Takes a mask and displays it in the terminal in a clear and easy to read way.
        This was used mainly for debugging the code and checking the masks I made
        were valid.

        Args:
            mask (str): A string of length 54 representing the mask pattern.
        """
        faces = copy.deepcopy(self.faces)
        counter = 0

        for i in range(6):
            for ii in range(3):
                for iii in range(3):
                    faces[i][ii][iii] = mask[counter]
                    counter += 1

        self.displayCube(faces)

    def analyseSolves(self, numSolves: int = 100, displayAllTimes: bool = True, displayStats: bool = True) -> dict:
        """Repeatedly randomises and solves the cube, tracking various statistics about the solves.

        Args:
            numSolves (int, optional): The number of solves to perform. Defaults to 100.
            displayAllTimes (bool, optional): If True, prints the time taken and number of rotations for each solve.
                                              Defaults to True.
            displayStats (bool, optional): If True, prints a summary of the statistics after all

        Returns:
            dict: A dictionary containing various statistics about the solves.
        """
        totalTime = 0
        totalMoves = 0
        totalCrossTime = 0
        maxCrossTime = 0
        totalCornersTime = 0
        maxCornersTime = 0
        totalMiddlesTime = 0
        maxMiddlesTime = 0
        totalLastLayerTime = 0
        maxLastLayerTime = 0
        totalMovesOptimised = 0
        for _ in range(numSolves):
            self.randomise()
            self.movesMade = []
            startTime = time.time()
            self.solveCross()
            crossTime = time.time()
            totalCrossTime += crossTime - startTime
            maxCrossTime = max(maxCrossTime, crossTime - startTime)
            self.solveF2LCorners()
            cornersTime = time.time()
            totalCornersTime += cornersTime - crossTime
            maxCornersTime = max(maxCornersTime, cornersTime - crossTime)
            self.solveF2LMiddlePieces()
            middlesTime = time.time()
            totalMiddlesTime += middlesTime - cornersTime
            maxMiddlesTime = max(maxMiddlesTime, middlesTime - cornersTime)
            self.solveLastLayer()
            lastLayerTime = time.time()
            totalLastLayerTime += lastLayerTime - middlesTime
            maxLastLayerTime = max(maxLastLayerTime, lastLayerTime - middlesTime)

            totalTime += lastLayerTime - startTime
            optimisedMoves = self.optimisedMoves
            if displayAllTimes:
                print(f"Time Taken : {round(lastLayerTime - startTime,2)} seconds")
                print(f"Number of Rotations: {len(optimisedMoves)}")

            totalMoves += len(self.movesMade)
            totalMovesOptimised += len(optimisedMoves)

        results = {
            "avg_time": round(totalTime / numSolves, 5),
            "avg_moves": round(totalMoves / numSolves, 5),
            "avg_moves_optimised": round(totalMovesOptimised / numSolves, 5),
            "avg_moves_saved": round((totalMoves - totalMovesOptimised) / numSolves, 2),
            "avg_cross_time": round(totalCrossTime / numSolves, 5),
            "avg_corners_time": round(totalCornersTime / numSolves, 5),
            "avg_middles_time": round(totalMiddlesTime / numSolves, 5),
            "avg_last_layer_time": round(totalLastLayerTime / numSolves, 5),
            "max_cross_time": round(maxCrossTime, 5),
            "max_corners_time": round(maxCornersTime, 5),
            "max_middles_time": round(maxMiddlesTime, 5),
            "max_last_layer_time": round(maxLastLayerTime, 5),
        }

        if displayStats:
            printAnalysis(results)

        return results


def _compileMacros(sequences: list[str]) -> tuple[list, list]:
    """Precompiles solve macros into single permutations plus their recorded move labels.

    Each macro is a fixed move sequence, so rather than replaying it move by move through
    executeSequence on every solve, we collapse it once into a single 54-square permutation
    (applied with one itemgetter gather) and capture the exact labels the sequence appends to
    movesMade. Both are read straight out of executeSequence run on a probe of 54 distinct
    squares, so applying the compiled form is byte-identical to the move-by-move path - same resulting
    state, same recorded moves - just far faster.

    Args:
        sequences (list[str]): The macro strings to compile (one table's move set).

    Returns:
        tuple[list, list]: Per-macro itemgetter permutations and per-macro move-label tuples.
    """
    getters, moves = [], []
    scratch = Cube()
    probe = "".join(chr(33 + i) for i in range(54))
    for seq in sequences:
        scratch.state = probe
        scratch.movesMade = []
        scratch.executeSequence(seq)
        perm = tuple(ord(ch) - 33 for ch in scratch.state)
        getters.append(operator.itemgetter(*perm))
        moves.append(tuple(scratch.movesMade))
    return getters, moves


# precompiled per-table macro permutations and their move labels; the table lookups already return
# the matching index into each list (cross -> POSSIBLE_ROTATIONS, the rest -> their INVERSE_MACROS)
_CROSS_GETTERS, _CROSS_MOVES = _compileMacros(POSSIBLE_ROTATIONS)
_CORNER_GETTERS, _CORNER_MOVES = _compileMacros(INVERSE_MACROS)
_MIDDLE_GETTERS, _MIDDLE_MOVES = _compileMacros(MIDDLE_INVERSE_MACROS)
_LL_GETTERS, _LL_MOVES = _compileMacros(LL_INVERSE_MACROS)
