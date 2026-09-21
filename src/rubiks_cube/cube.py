import copy
import logging
import operator
import random
import time

from .constants import *
from .corner_table import CORNER_PATHS, encodeCorners
from .cross_table import CROSS_PATHS, encodeCross
from .middle_table import MIDDLE_PATHS, encodeMiddles
from .last_layer_table import LAST_LAYER_PATHS, LAST_LAYER_KEY
from .cube_utils import checkMask, formatDuration, optimiseMoves, printAnalysis, rotate


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
        """Solves the cube stage by stage, each stage a single lookup in a precomputed table.

        This does the same work as calling solveCross, solveF2LCorners, solveF2LMiddlePieces and
        solveLastLayer in turn, but keeps the state in a local variable and only joins it back into
        a string at the end, rather than after every stage.

        The last layer needs no gather: reaching the end of it means the cube is solved, so the
        final state is SOLVED_MASK whichever entry got us there.

        Each of the first three tables is a list indexed by the stage's encode index rather than a
        dict, so a lookup costs no hashing. Together with the last layer's free state that takes a
        solve from ~11.3us to ~8.6us. Neither change touches how many moves a solve takes.
        """
        state = self.state
        moves = []
        # a stage with no entry in its table is already solved
        entry = CROSS_PATHS[encodeCross(state)]
        if entry is not None:
            # permutation applies the stage's whole solution in one gather, rather than executing
            # the moves in `labels` one by one
            permutation, labels = entry
            state = operator.itemgetter(*permutation)(state)
            moves += labels
        entry = CORNER_PATHS[encodeCorners(state)]
        if entry is not None:
            permutation, labels = entry
            state = operator.itemgetter(*permutation)(state)
            moves += labels
        entry = MIDDLE_PATHS[encodeMiddles(state)]
        if entry is not None:
            permutation, labels = entry
            state = operator.itemgetter(*permutation)(state)
            moves += labels
        labels = LAST_LAYER_PATHS.get(LAST_LAYER_KEY(state))
        if labels is not None:
            moves += labels
            self.state = SOLVED_MASK
        else:
            self.state = "".join(state)
        self.movesMade = moves

    def _applyPath(self, paths: list, index: int) -> None:
        """Applies a stage's whole precomputed solution to the cube in one step.

        An empty entry means the stage is already solved.

        Args:
            paths (list): The stage's table of precomputed solutions, indexed by encoded state.
            index (int): The encoded state to look up.
        """
        entry = paths[index]
        if entry is not None:
            permutation, labels = entry
            self.state = "".join(operator.itemgetter(*permutation)(self.state))
            self.movesMade.extend(labels)

    def solveCross(self) -> None:
        """Solves the white cross on the top of the cube.

        Looks up the whole solution for the current cross configuration in a precomputed table and
        applies it as a single permutation.
        """
        self._applyPath(CROSS_PATHS, encodeCross(self.state))

    def solveF2LCorners(self) -> None:
        """Solves the four white F2L corners.

        One lookup returns the entire cross-preserving solution for the current corner configuration,
        applied as a single permutation, so the corners are placed without disturbing the cross.
        """
        self._applyPath(CORNER_PATHS, encodeCorners(self.state))

    def solveF2LMiddlePieces(self) -> None:
        """Inserts the four middle-layer edges to complete the F2L.

        One lookup returns the entire cross-and-corner-preserving solution for the current middle-edge
        configuration, applied as a single permutation.
        """
        self._applyPath(MIDDLE_PATHS, encodeMiddles(self.state))

    def solveLastLayer(self) -> None:
        """Solves the entire last layer (the yellow face) in one table-driven pass.

        One lookup returns the entire F2L-neutral solution (preserves existing solved state)
        for the current last-layer configuration, finishing the cube without disturbing the first
        two layers.

        The table holds no permutation to apply: this stage finishes the cube, so the state it
        leaves behind is the solved one. That assumes the F2L really is solved, which is this
        stage's precondition - called on a cube whose first two layers are not done, the looked-up
        moves would not solve it and the state set here would be a lie.
        """
        labels = LAST_LAYER_PATHS.get(LAST_LAYER_KEY(self.state))
        if labels is not None:
            self.state = SOLVED_MASK
            self.movesMade.extend(labels)

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

        The scrambles are generated up front and the headline timing goes through solve(), so what
        is measured is the solver rather than the harness around it. Both of those matter more than
        they look: randomising between solves leaves every table lookup cold and cost ~5.5us a
        solve, and driving the four stage methods one at a time joins the state string four times
        instead of once for another ~5.4us. Timing each solve individually is free by comparison,
        so it stays.

        The per-stage split has to call the stages separately to attribute time to them, so it runs
        as a second pass and those four numbers still carry that overhead, over tables the first
        pass has already warmed. They do not reconcile with avg_time in either direction: compare
        the stages against each other, not against the total.

        Args:
            numSolves (int, optional): The number of solves to perform. Defaults to 100.
            displayAllTimes (bool, optional): If True, prints the time taken and number of rotations for each solve.
                                              Defaults to True.
            displayStats (bool, optional): If True, prints a summary of the statistics after all

        Returns:
            dict: A dictionary containing various statistics about the solves.
        """
        scrambles = []
        for _ in range(numSolves):
            self.randomise()
            scrambles.append(self.state)

        totalTime = 0
        totalMoves = 0
        totalMovesOptimised = 0
        for state in scrambles:
            self.state = state
            self.movesMade = []
            startTime = time.perf_counter()
            self.solve()
            solveTime = time.perf_counter() - startTime

            totalTime += solveTime
            optimisedMoves = self.optimisedMoves
            if displayAllTimes:
                print(f"Time Taken : {formatDuration(solveTime)}")
                print(f"Number of Rotations: {len(optimisedMoves)}")

            totalMoves += len(self.movesMade)
            totalMovesOptimised += len(optimisedMoves)

        # second pass, purely for the per-stage split
        totalCrossTime = 0
        maxCrossTime = 0
        totalCornersTime = 0
        maxCornersTime = 0
        totalMiddlesTime = 0
        maxMiddlesTime = 0
        totalLastLayerTime = 0
        maxLastLayerTime = 0
        for state in scrambles:
            self.state = state
            self.movesMade = []
            startTime = time.perf_counter()
            self.solveCross()
            crossTime = time.perf_counter()
            totalCrossTime += crossTime - startTime
            maxCrossTime = max(maxCrossTime, crossTime - startTime)
            self.solveF2LCorners()
            cornersTime = time.perf_counter()
            totalCornersTime += cornersTime - crossTime
            maxCornersTime = max(maxCornersTime, cornersTime - crossTime)
            self.solveF2LMiddlePieces()
            middlesTime = time.perf_counter()
            totalMiddlesTime += middlesTime - cornersTime
            maxMiddlesTime = max(maxMiddlesTime, middlesTime - cornersTime)
            self.solveLastLayer()
            lastLayerTime = time.perf_counter()
            totalLastLayerTime += lastLayerTime - middlesTime
            maxLastLayerTime = max(maxLastLayerTime, lastLayerTime - middlesTime)

        results = {
            # kept at full precision so the formatting below can show significant figures
            "avg_time": totalTime / numSolves,
            "avg_moves": round(totalMoves / numSolves, 5),
            "avg_moves_optimised": round(totalMovesOptimised / numSolves, 5),
            "avg_moves_saved": round((totalMoves - totalMovesOptimised) / numSolves, 2),
            "avg_cross_time": totalCrossTime / numSolves,
            "avg_corners_time": totalCornersTime / numSolves,
            "avg_middles_time": totalMiddlesTime / numSolves,
            "avg_last_layer_time": totalLastLayerTime / numSolves,
            "max_cross_time": maxCrossTime,
            "max_corners_time": maxCornersTime,
            "max_middles_time": maxMiddlesTime,
            "max_last_layer_time": maxLastLayerTime,
        }

        if displayStats:
            printAnalysis(results)

        return results
