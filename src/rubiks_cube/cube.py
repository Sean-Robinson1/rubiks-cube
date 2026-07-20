import copy
import logging
import random
import time

from .constants import *
from .cross_table import CROSS_TABLE, NO_MOVE, encodeCross
from .cube_utils import checkMask, combineMasks, matchesAnySparse, optimiseMoves, printAnalysis, rotate, sparsifyMasks


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

            moveLabel = ch + ("i" if direction == -1 else "")
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
        self.solveYellowCross()
        self.alignYellowEdges()
        self.solveYellowCorners()
        self.final()

    def solveCross(self) -> None:
        """Solves the white cross on the top of the cube.

        Uses a precomputed table that maps every white-cross configuration to the next move on an
        optimal path to the solved cross, so the cross is solved by a short sequence of O(1) lookups
        rather than a search.
        """
        move = CROSS_TABLE[encodeCross(self.state)]
        while move != NO_MOVE:
            self.executeSequence(POSSIBLE_ROTATIONS[move])
            move = CROSS_TABLE[encodeCross(self.state)]

    def solveF2LCorners(self) -> None:
        """Solves all white corner pieces as part of the F2L (First 2 Layers) solution."""

        insertionMasks = set(F2L_CORNERS_INSERTION_MASKS)
        solvedMasks = set(F2L_CORNERS_SOLVED_MASKS)

        # searches until all 4 corners are correctly placed
        insertedCorners = 0
        while insertedCorners != 4:
            toRemove = []
            for mask in solvedMasks:
                if self.checkMask(mask[1]):
                    toRemove.append(mask)
                    filtered = filter(lambda x: x[0][0] != mask[0], insertionMasks)
                    insertionMasks = set(map(lambda a: (a[0], combineMasks(a[1], mask[1])), filtered))
                    insertedCorners += 1

            for masks in toRemove:
                solvedMasks.remove(masks)

            if insertedCorners == 4:
                break

            inserted = False
            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.__insertCorner(mask[0])
                    inserted = True

            if inserted:
                continue

            recurseMasks = list(map(lambda x: x[1], insertionMasks))
            moves = self.__startPathfinding(recurseMasks, 2)

            if moves is None:
                for face, mask in solvedMasks:
                    self.__insertCorner(face + "_2")
                    break
            else:
                self.executeSequence("".join(moves))

            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.__insertCorner(mask[0])

    def __insertCorner(self, code: str) -> None:
        """Inserts a corner piece correctly as part of the F2L (First 2 Layers) solution,
        using the code to determine method of insertion/algorithm.

        Args:
            code (str): A string in the format "XYn", where X is the first face colour, Y is the second face colour,
                        and n is the insertion method (1, 2, or 3).
        """
        face = code[0]
        insertionMethod = int(code[2])
        self.convertSequenceFromFace(face, CORNER_INSERTION_ALGORITHMS[insertionMethod])

    def solveF2LMiddlePieces(self) -> None:
        """Inserts the middle layer edge pieces correctly as part of the F2L (First 2 Layers) solution."""

        solvedMasks = set(F2L_MIDDLE_SOLVED_MASKS)
        insertionMasks = set(F2L_MIDDLE_INSERTION_MASKS)

        correctPieces = 0
        while correctPieces != 4:
            toRemove = []
            for mask in solvedMasks:
                if self.checkMask(mask[1]):
                    toRemove.append(mask)
                    filtered = filter(lambda x: sorted(x[0]) != sorted(mask[0]), insertionMasks)
                    insertionMasks = list(map(lambda a: (a[0], combineMasks(a[1], mask[1])), filtered))
                    correctPieces += 1

            for masks in toRemove:
                solvedMasks.remove(masks)

            if correctPieces == 4:
                break

            inserted = False
            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.__insertPiece(mask[0])
                    inserted = True

            if inserted:
                continue

            recurseMasks = list(map(lambda x: x[1], insertionMasks))
            moves = self.__startPathfinding(recurseMasks, 2)

            if moves is None:
                for face, mask in solvedMasks:
                    self.__insertPiece(face)
            else:
                self.executeSequence("".join(moves))

            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.__insertPiece(mask[0])

    def solveYellowCross(self) -> None:
        """Solves the yellow cross."""

        alg = YELLOW_CROSS_INSERTION_ALGORITHM

        while not self.checkMask(YELLOW_CROSS_SOLVED_MASK):
            executed = False
            for face, mask in YELLOW_L_MASKS:
                if self.checkMask(mask):
                    self.convertSequenceFromFace(face, alg)
                    executed = True
                    break

            for face, mask in YELLOW_LINE_MASKS:
                if self.checkMask(mask):
                    self.convertSequenceFromFace(face, alg)
                    executed = True
                    break

            if not executed:
                self.executeSequence(alg)

    def alignYellowEdges(self) -> None:
        """Aligns the yellow edges so the corners can be inserted."""
        while not self.checkMask(YELLOW_EDGES_SOLVED_MASK):
            # compare each side's centre (face*9 + 4) with its bottom-row middle (face*9 + 7)
            # straight from the state string instead of decoding the whole cube
            s = self.state
            numMatches = 0
            notMatchingFaces = []
            for face in range(1, 5):
                if s[face * 9 + 4] == s[face * 9 + 7]:
                    numMatches += 1
                else:
                    notMatchingFaces.append(s[face * 9 + 4])

            if numMatches == 4:
                return

            elif numMatches == 2:
                face1 = notMatchingFaces[0]
                face2 = notMatchingFaces[1]
                if self.getOppositeFace(face1) == face2:
                    self.convertSequenceFromFace(face1, "D" + YELLOW_EDGES_INSERTION_ALGORITHM)
                    self.convertSequenceFromFace(self.getLeftFace(face1), YELLOW_EDGES_INSERTION_ALGORITHM)
                else:
                    if self.getLeftFace(face1) == face2:
                        self.convertSequenceFromFace(face2, YELLOW_EDGES_INSERTION_ALGORITHM)
                    else:
                        self.convertSequenceFromFace(face1, YELLOW_EDGES_INSERTION_ALGORITHM)
            else:
                self.executeSequence("D")

    def __checkValidCorners(self) -> list[str]:
        """Checks how many of the 4 corners for the yellow face are in the correct position.

        Returns:
            list[str]: A list of face colours that have valid corners.
        """
        # read the twelve corner squares straight out of the state string (index = face*9 + row*3 + col)
        # rather than decoding the whole cube into a nested list
        s = self.state
        validCorners = []
        if (
            s[26] in {"R", "Y", "B"}  # faces[2][2][2]
            and s[33] in {"R", "Y", "B"}  # faces[3][2][0]
            and s[47] in {"R", "Y", "B"}  # faces[5][0][2]
        ):
            validCorners.append("B")
        if (
            s[35] in {"O", "Y", "B"}  # faces[3][2][2]
            and s[42] in {"O", "Y", "B"}  # faces[4][2][0]
            and s[53] in {"O", "Y", "B"}  # faces[5][2][2]
        ):
            validCorners.append("O")
        if (
            s[44] in {"O", "Y", "G"}  # faces[4][2][2]
            and s[15] in {"O", "Y", "G"}  # faces[1][2][0]
            and s[51] in {"O", "Y", "G"}  # faces[5][2][0]
        ):
            validCorners.append("G")
        if (
            s[17] in {"R", "Y", "G"}  # faces[1][2][2]
            and s[24] in {"R", "Y", "G"}  # faces[2][2][0]
            and s[45] in {"R", "Y", "G"}  # faces[5][0][0]
        ):
            validCorners.append("R")

        return validCorners

    def solveYellowCorners(self) -> None:
        """Correctly orients the yellow corners."""

        while True:
            validCorners = self.__checkValidCorners()
            if len(validCorners) == 4:
                return

            elif len(validCorners) == 0:
                self.executeSequence(YELLOW_CORNERS_INSERTION_ALGORITHM)

            else:
                for _ in range(3):
                    self.convertSequenceFromFace(validCorners[0], YELLOW_CORNERS_INSERTION_ALGORITHM)
                    if len(self.__checkValidCorners()) == 4:
                        return

    def final(self) -> None:
        """Finalizes the solution by orienting the last layer."""
        while not self.checkMask(SOLVED_MASK):
            # face 5 (bottom), row 0, column 0 is state index 45
            if self.state[45] != "Y":
                while self.state[45] != "Y":
                    self.executeSequence(FINAL_STEP_ALGORITHM)
            self.executeSequence("D")

    def __insertPiece(self, code: str) -> None:
        """Correctly inserts a piece into the middle layer.

        Args:
            code (str): A string in the format "XY", where X is the first face colour and Y is the second face colour.
        """
        face = code[0]
        otherFace = code[1]

        if otherFace == self.getLeftFace(face):
            self.convertSequenceFromFace(face, LEFT_FACE_INSERTION_ALGORITHM)
        else:
            self.convertSequenceFromFace(face, RIGHT_FACE_INSERTION_ALGORITHM)

    def __startPathfinding(self, masks: list[str], depth: int = 6) -> list[str] | None:
        """Calls a function to perform DFS until a solution is found or the maximum depth is reached.

        Args:
            masks (list[str]): A list of masks to search for.
            depth (int, optional): The maximum depth to search. Defaults to 6.

        Returns:
            list[str] | None: A list of moves to reach one of the masks, or None if no solution was found.
        """
        if not any(map(lambda x: self.checkMask(x), masks)):
            # decompose the masks into their non-dot squares once, so the recursive search
            # tests every state against them without re-looking-up each mask's sparse form.
            # the transposition table only pays off for the deep cross search - at shallow depths
            # its ~13 stored states never collide, so skip it (None) to avoid pure overhead
            visited = None if depth <= 2 else {}
            result = self.__pathfind(sparsifyMasks(masks), depth, str(self), visited)
            if result is not None:
                return result
            else:
                return None

        return []

    def __pathfind(
        self, sparseMasks: list[tuple[tuple[int, str], ...]], depth: int, state: str, visited: dict[str, int] | None
    ) -> list[str] | None:
        """Performs DFS until a solution is found or the maximum depth is reached. Has some optimisations.

        Args:
            sparseMasks (list): The target masks, pre-decomposed by sparsifyMasks.
            depth (int): The maximum depth to search.
            state (str): The current state of the cube as a string.
            visited (dict[str, int] | None): Transposition table mapping a state to the greatest
                                             remaining depth it has already been explored with, or
                                             None to search without one (used for shallow searches).

        Returns:
            list[str] | None: A list of moves to reach one of the masks, or None if no solution was found.
        """
        if matchesAnySparse(sparseMasks, state):
            return []

        if depth == 0:
            return None

        # transposition table: if this state was already explored with at least as
        # much remaining depth, that subtree was fully searched without success, so skip it
        if visited is not None:
            if visited.get(state, -1) >= depth:
                return None
            visited[state] = depth

        for move in range(12):
            newstate = rotate(state, POSSIBLE_ROTATIONS[move])
            result = self.__pathfind(sparseMasks, depth - 1, newstate, visited)

            if result is not None:
                return [POSSIBLE_ROTATIONS[move]] + result

        return None

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
        totalYellowCrossTime = 0
        maxYellowCrossTime = 0
        totalYellowEdgesTime = 0
        maxYellowEdgesTime = 0
        maxFinalTime = 0
        totalFinalTime = 0
        totalMovesOptimised = 0
        for _ in range(numSolves):
            self.randomise()
            self.movesMade = []
            startTime = time.time()
            self.solveCross()
            totalCrossTime += time.time() - startTime
            crossTime = time.time()
            maxCrossTime = max(maxCrossTime, crossTime - startTime)
            self.solveF2LCorners()
            totalCornersTime += time.time() - crossTime
            cornersTime = time.time()
            maxCornersTime = max(maxCornersTime, cornersTime - crossTime)
            self.solveF2LMiddlePieces()
            totalMiddlesTime += time.time() - cornersTime
            middlesTime = time.time()
            maxMiddlesTime = max(maxMiddlesTime, middlesTime - cornersTime)
            self.solveYellowCross()
            totalYellowCrossTime += time.time() - middlesTime
            yellowCrossTime = time.time()
            maxYellowCrossTime = max(maxYellowCrossTime, yellowCrossTime - middlesTime)
            self.alignYellowEdges()
            totalYellowCrossTime += time.time() - yellowCrossTime
            yellowEdgesTime = time.time()
            maxYellowEdgesTime = max(maxYellowEdgesTime, yellowEdgesTime - yellowCrossTime)
            self.solveYellowCorners()
            totalYellowEdgesTime += time.time() - yellowEdgesTime
            yellowEdgesTime = time.time()
            maxYellowEdgesTime = max(maxYellowEdgesTime, yellowEdgesTime - yellowEdgesTime)
            self.final()
            totalFinalTime += time.time() - yellowEdgesTime
            yellowFaceTime = time.time()
            maxFinalTime = max(maxFinalTime, yellowFaceTime - yellowEdgesTime)

            totalTime += yellowFaceTime - startTime
            optimisedMoves = self.optimisedMoves
            if displayAllTimes:
                print(f"Time Taken : {round(yellowFaceTime - startTime,2)} seconds")
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
            "avg_yellow_cross_time": round(totalYellowCrossTime / numSolves, 5),
            "avg_yellow_edges_time": round(totalYellowEdgesTime / numSolves, 5),
            "avg_final_time": round(totalFinalTime / numSolves, 5),
            "max_cross_time": round(maxCrossTime, 5),
            "max_corners_time": round(maxCornersTime, 5),
            "max_middles_time": round(maxMiddlesTime, 5),
            "max_yellow_cross_time": round(maxYellowCrossTime, 5),
            "max_yellow_edges_time": round(maxYellowEdgesTime, 5),
            "max_final_time": round(maxFinalTime, 5),
        }

        if displayStats:
            printAnalysis(results)

        return results
