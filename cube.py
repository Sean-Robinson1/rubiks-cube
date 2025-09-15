import random
import time
import copy
from cube_utils import rotate, checkMask, printAnalysis, optimiseMoves
from constants import *

class Cube:
    def __init__(self, startStr: str = None) -> None:
        self.faces: list[list[str]] = [[[colour] * 3 for _ in range(3)] for colour in COLOURS]
        self.initialiseFaces(startStr)
        self.calculateFaces('R','W')

        self.movesMade = []

    def __str__(self) -> str:
        outputString = ''
        for face in range(6):
            for row in self.faces[face]:
                for square in row:
                    outputString += square
        return outputString

    def __getitem__(self, index: int) -> list[list[str]]:
        return self.faces[index]
    
    @property
    def optimisedMoves(self) -> list[str]:
        return optimiseMoves(self.movesMade)
    
    def initialiseFaces(self, faceStr: str | None) -> None:
        """Initialises the faces of the cube from a string representation.
        
        Args:
            faceStr (str | None): A string of length 54 representing the cube's faces.
        """
        if faceStr:
            self.faces = []
            counter = 0
            for _ in range(0,6):
                face = []
                for ii in range(3):
                    face.append([])
                    for _ in range(3):
                        face[ii].append(faceStr[counter])
                        counter += 1

                self.faces.append(face)

    def calculateFaces(self, front: str, top: str) -> None:
        """Calculates faces relative to a chosen front face and a chosen top face.
        
        Note - this assumes the two faces are not opposites.

        Args:
            front (str): The colour of the front face.
            top (str): The colour of the top face.
        """
        self.top = top
        self.front = front
        self.bottom = self.getOppositeFace(top)
        self.back = self.getOppositeFace(front)
        self.left = FACE_NUM_TO_COLOUR[((COLOUR_TO_FACE_NUM[self.front] - 2) % 4) + 1]
        self.right = self.getOppositeFace(self.left)

    def getPlottingList(self) -> list[str]:
        """Returns a list of colours in the correct order to be plotted.
        
        Returns:
            list[str]: A list of colours in the order required for plotting.
        """
        outputList = []
        for face in [(0,-1,1),(5,1,1),(2,1,1),(4,1,-1),(1,1,-1),(3,1,1)]:
            for row in self.faces[face[0]][::face[1]]:
                for square in row[::face[2]]:
                    outputList.append(PLOTTING_COLOUR_MAP[square])
        return outputList

    def displayCube(self, faces: list[list[str]] = None) -> None:
        """Displays the cube in the console. If no faces are provided, the current state of the cube is displayed.
        
        Args:
            faces (list[list[str]], optional): A 2D list representing the cube's faces. Defaults to None.
        """
        if faces is None:
            faces = self.faces

        print('\n\n')
        
        for row in faces[0]:
            print(10*' ',end='')
            for square in row:
                print(COLOUR_TO_UNICODE.get(square,ERROR_CHAR),end=' ')
            print()

        for row in range(3):
            for faceIndex in range(1,5):
                face = faces[faceIndex]

                for square in face[row]:
                    print(COLOUR_TO_UNICODE.get(square,ERROR_CHAR),end=' ')
                print(' ',end='')
            print()

        for row in faces[5]:
            print(10*' ',end='')
            for square in row:
                print(COLOUR_TO_UNICODE.get(square,ERROR_CHAR),end=' ')
            print()

    def randomiseCube(self) -> list[str]:
        """Randomises the cube to a valid state.
        
        Returns:
            list[str]: The sequence of moves used to randomise the cube.
        """
        turns = ['R','L','U','D','F','B']
        sequence = []
        for _ in range(50):
            move = turns[random.randint(0,5)]

            if random.random() > 0.5:
                move += 'i'

            sequence.append(move)
        
        self.executeSequence(''.join(sequence))
        return sequence

    def workBackwards(self, sequence: list[str]) -> None:
        """Given the sequence of moves that scrambled/randomised the cube, this
        function will work backwards and solve the cube. This method is often
        used to fake solving the cube, specifically cubes of much larger sizes.

        Args:
            sequence (list[str]): The sequence of moves that scrambled the cube.
        """
        sequence2 = ''
        for i in range(len(sequence)-1,-1,-1):
            turn = sequence[i]
            print(turn)

            if len(turn) == 2:
                sequence2 += turn[0]
            else:
                sequence2 += turn + 'i'

        self.executeSequence(sequence2)

    def rotateU(self, direction: int = 0) -> None:
        """Performs a rotation of the upper face.
        
        Args:
            direction (int, optional): The direction to rotate the face. 0 for clockwise, 1 for counter-clockwise. Defaults to 0.
        """
        if direction == 0:
            self.faces[4][0],self.faces[1][0],self.faces[2][0],self.faces[3][0] = self.faces[1][0],self.faces[2][0],self.faces[3][0],self.faces[4][0]
            self.rotateFace(0)
        else:
            self.faces[1][0],self.faces[2][0],self.faces[3][0],self.faces[4][0] = self.faces[4][0],self.faces[1][0],self.faces[2][0],self.faces[3][0]
            self.rotateFace(0,-1)

    def rotateD(self, direction:int = 0) -> None:
        """Performs a rotation of the down face.

        Args:
            direction (int, optional): The direction to rotate the face. 0 for clockwise, 1 for counter-clockwise. Defaults to 0.
        """
        if direction == 0:
            self.faces[1][2],self.faces[2][2],self.faces[3][2],self.faces[4][2] = self.faces[4][2],self.faces[1][2],self.faces[2][2],self.faces[3][2]  
            self.rotateFace(5)
        else:
            self.faces[4][2],self.faces[1][2],self.faces[2][2],self.faces[3][2] = self.faces[1][2],self.faces[2][2],self.faces[3][2],self.faces[4][2]
            self.rotateFace(5,-1)

    def rotateF(self, direction: int = 0) -> None:
        """Performs a rotation of the front face.

        Args:
            direction (int, optional): The direction to rotate the face. 0 for clockwise, 1 for counter-clockwise. Defaults to 0.
        """
        if direction == 0:
            self.rotateFace(2)

            for i in range(3):
                self.faces[1][2-i][2], self.faces[0][2][i], self.faces[3][i][0], self.faces[5][0][2-i] = self.faces[5][0][2-i], self.faces[1][2-i][2], self.faces[0][2][i], self.faces[3][i][0]

        else:
            self.rotateFace(2,-1)

            for i in range(3):
                self.faces[1][2-i][2], self.faces[0][2][i], self.faces[3][i][0], self.faces[5][0][2-i] = self.faces[0][2][i], self.faces[3][i][0], self.faces[5][0][2-i], self.faces[1][2-i][2]

    def rotateB(self, direction: int = 0) -> None:
        """Performs a rotation of the back face.

        Args:
            direction (int, optional): The direction to rotate the face. 0 for clockwise, 1 for counter-clockwise. Defaults to 0.
        """
        if direction == 0:
            self.rotateFace(4)
            for i in range(3):
                self.faces[1][2-i][0], self.faces[0][0][i], self.faces[3][i][2], self.faces[5][2][2-i] = self.faces[0][0][i], self.faces[3][i][2], self.faces[5][2][2-i], self.faces[1][2-i][0]
           
        else:
            self.rotateFace(4,-1)
            for i in range(3):
                self.faces[1][2-i][0], self.faces[0][0][i], self.faces[3][i][2], self.faces[5][2][2-i] = self.faces[5][2][2-i], self.faces[1][2-i][0], self.faces[0][0][i], self.faces[3][i][2]

    def rotateR(self, direction: int = 0) -> None:
        """Performs a rotation of the right face.

        Args:
            direction (int, optional): The direction to rotate the face. 0 for clockwise, 1 for counter-clockwise. Defaults to 0.
        """
        if direction == 0:
            self.rotateFace(3)
            for i in range(3):
                self.faces[2][2-i][2], self.faces[0][2-i][2], self.faces[4][i][0], self.faces[5][2-i][2] = self.faces[5][2-i][2], self.faces[2][2-i][2], self.faces[0][2-i][2], self.faces[4][i][0]
           
        else:
            self.rotateFace(3,-1)
            for i in range(3):
                self.faces[2][2-i][2], self.faces[0][2-i][2], self.faces[4][i][0], self.faces[5][2-i][2] = self.faces[0][2-i][2], self.faces[4][i][0], self.faces[5][2-i][2], self.faces[2][2-i][2]   

    def rotateL(self, direction: int = 0) -> None:
        """Performs a rotation of the left face.

        Args:
            direction (int, optional): The direction to rotate the face. 0 for clockwise, 1 for counter-clockwise. Defaults to 0.
        """
        if direction == 0:
            self.rotateFace(1)
            for i in range(3):
                self.faces[2][2-i][0], self.faces[0][2-i][0], self.faces[4][i][2], self.faces[5][2-i][0] = self.faces[0][2-i][0], self.faces[4][i][2], self.faces[5][2-i][0], self.faces[2][2-i][0]

        else:
            self.rotateFace(1,-1)

            for i in range(3):
                self.faces[2][2-i][0], self.faces[0][2-i][0], self.faces[4][i][2], self.faces[5][2-i][0] = self.faces[5][2-i][0], self.faces[2][2-i][0], self.faces[0][2-i][0], self.faces[4][i][2]

    def rotateFace(self, face: int = 2, direction: int = 0) -> None:
        """Rotates the specified face of the cube 90 degrees clockwise or anti-clockwise.

        Args:
            face (int, optional): The face to rotate. Defaults to 2 (the front face).
            direction (int, optional): The direction to rotate the face. 0 for clockwise, 1 for counter-clockwise. Defaults to 0.
        """
        squares = []

        if direction == 0:
            order = CLOCKWISE_TURNS
        else:
            order = ANTI_CLOCKWISE_TURNS

        for square in SPIRAL_ORDER:
            column = square % 3
            row = square // 3

            squares.append(self.faces[face][row][column])

        for squareIndex in range(len(order)):
            square = order[squareIndex]
            column = square % 3
            row = square // 3

            self.faces[face][row][column] = squares[(squareIndex)]

    def executeSequence(self, sequence: str, useColours: bool = False) -> None:
        """Executes a sequence of moves on the Rubik's Cube.

        Args:
            sequence (str): A string representing the sequence of moves to execute.
            useColours (bool, optional): If True, uses colour notation (R, G, W, Y, B, O) instead of face notation (R, L, U, D, F, B). Defaults to False.
        """
        seq = sequence.replace(' ', '')

        if not useColours:
            letterToFunc = {'R': self.rotateR, 'L': self.rotateL, 'U': self.rotateU,
                            'D': self.rotateD, 'F': self.rotateF, 'B': self.rotateB}
        else:
            letterToFunc = {'B': self.rotateR, 'G': self.rotateL, 'W': self.rotateU,
                            'Y': self.rotateD, 'R': self.rotateF, 'O': self.rotateB}

        i = 0
        while i < len(seq):
            ch = seq[i]
            if ch not in letterToFunc:
                i += 1
                continue

            func = letterToFunc[ch]
            direction = 0
            repeats = 1
            j = i + 1

            if j < len(seq) and seq[j] in ("'", "i"):
                direction = -1
                j += 1

            elif j < len(seq) and seq[j].isdigit():
                numStr = ''
                while j < len(seq) and seq[j].isdigit():
                    numStr += seq[j]
                    j += 1
                try:
                    repeats = max(1, int(numStr))
                except ValueError:
                    repeats = 1

            moveLabel = ch + ('i' if direction == -1 else '')
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
        stringVersion = str(self)
        for i in range(len(mask)):
            if mask[i] != '.' and mask[i] != stringVersion[i]:
                return False
        return True

    def getOppositeFace(self, colour: str) -> str:
        """Returns the opposite face relative to the given face colour
        
        Args:
            colour (str): The colour of the face.

        Returns:
            str: The colour of the opposite face.    
        """
        return OPPOSITE_FACE_MAPPING.get(colour, None)

    def getLeftFace(self, colour: str) -> str:
        """Returns the left face relative to the given face colour.

        Note - this assumes the white face is currently at the top.
        
        Args:
            colour (str): The colour of the face.

        Returns:
            str: The colour of the left face.
        """
        return LEFT_FACE_MAPPING.get(colour, None)

    def getRightFace(self, colour: str) -> str:
        """Returns the right face relative to the given face colour.

        Note - this assumes the white face is currently at the top.

        Args:
            colour (str): The colour of the face.

        Returns:
            str: The colour of the right face.
        """
        return RIGHT_FACE_MAPPING.get(colour, None)

    def executeSequenceRelative(self, sequence: str) -> None:
        """Executes a sequence of moves relative to the current front and top faces.

        Args:
            sequence (str): A string representing the sequence of moves to execute.
        """
        out = ""

        letterToFace = {'R': self.right, 'L': self.left, 'F': self.front, 'B': self.back, 'U': self.top, 'D': self.bottom}

        for letter in sequence:
            out += letterToFace.get(letter, letter)

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
            out += RELATIVE_FACE_MAPPING.get(face,{}).get(letter,letter)

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
        """Solves the white cross on the top of the cube."""

        solvedMasks = copy.deepcopy(WHITE_CROSS_SOLVED_MASKS)
        recurseMasks = copy.deepcopy(WHITE_CROSS_RECURSION_MASKS)
        insertionMasks = copy.deepcopy(WHITE_CROSS_INSERTION_MASKS)

        numCorrect = 0
        removed = "." * 54
        while numCorrect != 4:
            toRemove = []
            for face, mask, pattern in insertionMasks:
                if self.checkMask(mask):
                    toRemove.append((face,mask,pattern))
                    recurseMasks.discard(mask)
                    self.convertSequenceFromFace(face,pattern)

            for item in toRemove:
                insertionMasks.remove(item)

            toRemove = []
            for face, mask in solvedMasks:
                if self.checkMask(mask):
                    toRemove.append((face,mask))
                    numCorrect += 1

            if numCorrect == 4:
                break

            for item in toRemove:
                solvedMasks.remove(item)
                removed = self.combineMasks(removed,item[1])

            if len(toRemove) > 0:
                recurseMasks = set(map(lambda x : self.combineMasks(x,removed),recurseMasks))
                insertionMasks = set(map(lambda x : (x[0],self.combineMasks(x[1],removed),x[2]),insertionMasks))

            recurseMasks = set(filter(lambda x : not self.checkMask(x), recurseMasks))

            moves = self.recurseToMasks(recurseMasks,5) 

            if moves is None:
                for face, mask in solvedMasks:
                    if not self.checkMask(mask):
                        self.convertSequenceFromFace(face,"FU'RU")
                        
            if moves is not None:
                self.executeSequence("".join(moves))

    def solveF2LCorners(self) -> None:
        """Solves all white corner pieces as part of the F2L (First 2 Layers) solution."""
        
        insertionMasks = copy.deepcopy(F2L_CORNERS_INSERTION_MASKS)

        correctPieces = 0
        while correctPieces != 4:
            correctPieces = 0
            for mask in F2L_CORNERS_SOLVED_MASKS:
                if self.checkMask(mask[1]):
                    filtered = filter(lambda x: x[0][0] != mask[0],insertionMasks)
                    insertionMasks = list(map(lambda a: (a[0],self.combineMasks(a[1],mask[1])),filtered))
                    correctPieces += 1

            if correctPieces == 4:
                break
            
            inserted = False
            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.insertCorner(mask[0])
                    inserted = True

            if inserted:
                continue

            recurseMasks = list(map(lambda x: x[1],insertionMasks))
            moves = self.recurseToMasks(recurseMasks,2)

            if moves is None:
                for face, mask in F2L_CORNERS_SOLVED_MASKS:
                    if not self.checkMask(mask):
                        self.insertCorner(face+"_2")
                        break
            else:
                self.executeSequence("".join(moves))

            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.insertCorner(mask[0])

    def insertCorner(self, code: str) -> None:
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

        solvedMasks = copy.deepcopy(F2L_MIDDLE_SOLVED_MASKS)

        insertionMasks = copy.deepcopy(F2L_MIDDLE_INSERTION_MASKS)

        correctPieces = 0
        while correctPieces != 4:
            correctPieces = 0
            for mask in solvedMasks:
                if self.checkMask(mask[1]):
                    filtered = filter(lambda x: sorted(x[0]) != sorted(mask[0]),insertionMasks)
                    insertionMasks = list(map(lambda a: (a[0],self.combineMasks(a[1],mask[1])),filtered))
                    correctPieces += 1

            if correctPieces == 4:
                break
            
            inserted = False
            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.insertPiece(mask[0])
                    inserted = True

            if inserted:
                continue

            recurseMasks = list(map(lambda x: x[1],insertionMasks))
            moves = self.recurseToMasks(recurseMasks,2)

            if moves is None:
                for face, mask in solvedMasks:
                    if not self.checkMask(mask):
                        self.insertPiece(face)
                        break
            else:
                self.executeSequence("".join(moves))

            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.insertPiece(mask[0])

    def solveYellowCross(self) -> None:
        """Solves the yellow cross."""

        # the insertion algorithm
        alg = YELLOW_CROSS_INSERTION_ALGORITHM

        while not self.checkMask(YELLOW_CROSS_SOLVED_MASK):
            executed = False
            for face,mask in YELLOW_L_MASKS:
                if self.checkMask(mask):
                    self.convertSequenceFromFace(face,alg) 
                    executed = True
                    break

            for face,mask in YELLOW_LINE_MASKS:
                if self.checkMask(mask):
                    self.convertSequenceFromFace(face,alg) 
                    executed = True
                    break
            
            if not executed:
                self.executeSequence(alg)

    def alignYellowEdges(self) -> None:
        """Aligns the yellow edges so the corners can be inserted."""
        while not self.checkMask(YELLOW_EDGES_SOLVED_MASK):
            numMatches = 0
            notMatchingFaces = []
            for face in range(1,5):
                if self.faces[face][1][1] == self.faces[face][2][1]:
                    numMatches += 1 
                else:
                    notMatchingFaces.append(self.faces[face][1][1])

            if numMatches == 4:
                return 
            
            elif numMatches == 2:
                face1 = notMatchingFaces[0]
                face2 = notMatchingFaces[1]
                if self.getOppositeFace(face1) == face2: 
                    self.convertSequenceFromFace(face1, "D" + YELLOW_EDGES_INSERTION_ALGORITHM)
                    self.convertSequenceFromFace(self.getLeftFace(face1),YELLOW_EDGES_INSERTION_ALGORITHM)
                else:
                    if self.getLeftFace(face1) == face2:
                        self.convertSequenceFromFace(face2, YELLOW_EDGES_INSERTION_ALGORITHM)
                    else:
                        self.convertSequenceFromFace(face1, YELLOW_EDGES_INSERTION_ALGORITHM)
            else:
                self.executeSequence('D')

    def checkValidCorners(self) -> list[str]:
        """Checks how many of the 4 corners for the yellow face are in the correct position. Returns a list of all valid face colours.
        
        Returns:
            list[str]: A list of face colours that have valid corners.
        """
        validCorners = []
        if self.faces[2][2][2] in {'R','Y','B'} and self.faces[3][2][0] in {'R','Y','B'} and self.faces[5][0][2] in {'R','Y','B'}:
            validCorners.append('B')
        if self.faces[3][2][2] in {'O','Y','B'} and self.faces[4][2][0] in {'O','Y','B'} and self.faces[5][2][2] in {'O','Y','B'}:
            validCorners.append('O')
        if self.faces[4][2][2] in {'O','Y','G'} and self.faces[1][2][0] in {'O','Y','G'} and self.faces[5][2][0] in {'O','Y','G'}:
            validCorners.append('G')
        if self.faces[1][2][2] in {'R','Y','G'} and self.faces[2][2][0] in {'R','Y','G'} and self.faces[5][0][0] in {'R','Y','G'}:
            validCorners.append('R')

        return validCorners

    def solveYellowCorners(self) -> None:
        """Correctly orients the yellow corners."""
        validCorners = self.checkValidCorners()

        if len(validCorners) == 4:
            return 
        
        elif len(validCorners) == 0:
            self.executeSequence(YELLOW_CORNERS_INSERTION_ALGORITHM)
            self.solveYellowCorners()

        else:
            for _ in range(3):
                self.convertSequenceFromFace(validCorners[0],YELLOW_CORNERS_INSERTION_ALGORITHM)
                if len(self.checkValidCorners()) == 4:
                    return
            self.solveYellowCorners()

    def final(self) -> None:
        """Finalizes the solution by orienting the last layer."""
        while not self.checkMask(SOLVED_MASK):
            if self.faces[5][0][0] != 'Y':
                while self.faces[5][0][0] != 'Y':
                    self.executeSequence(FINAL_STEP_ALGORITHM)
            self.executeSequence("D")

    def insertPiece(self, code: str) -> None:
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

    def recurseToMasks(self, masks: list[str], depth: int = 6) -> list[str] | None:
        """Calls a function to perform DFS until a solution is found or the maximum depth is reached.
        
        Args:
            masks (list[str]): A list of masks to search for.
            depth (int, optional): The maximum depth to search. Defaults to 6.

        Returns:
            list[str] | None: A list of moves to reach one of the masks, or None if no solution was found within the depth.
        """
        cache = {}
        if not any(map(lambda x: self.checkMask(x), masks)):
            result = self.findMasksRecursion(masks, depth, str(self), cache)
            if result is not None:
                return result
            else:
                return None

        return []

    def findMasksRecursion(self, masks: list[str], depth: int, state: str, cache: dict) -> list[str] | None:
        """Performs DFS until a solution is found or the maximum depth is reached. Has some optimisations.
                
        Args:
            masks (list[str]): A list of masks to search for.
            depth (int): The maximum depth to search.
            state (str): The current state of the cube as a string.
            cache (dict): A dictionary to cache previously computed states.

        Returns:
            list[str] | None: A list of moves to reach one of the masks, or None if no solution was found within the depth.
        """
        cache_key = state
        if cache_key in cache:
            return cache[cache_key]
        
        for mask in masks:
            if checkMask(mask, state):
                cache[cache_key] = []
                return []
        
        if depth == 0:
            return None

        for move in range(12):
            newstate = rotate(state,POSSIBLE_ROTATIONS[move])
            result = self.findMasksRecursion(masks,depth-1,newstate,cache)

            if result is not None:
                cache[cache_key] = [POSSIBLE_ROTATIONS[move]] + result
                return cache[cache_key]
        
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

    def combineMasks(self, mask1: str, mask2: str) -> str:
        """Combines two masks. If they both specify a certain square differently,
        priority will be given to mask1, and the output mask will take the value
        mask1 assigns to that square.

        Args:
            mask1 (str): The first mask to combine.
            mask2 (str): The second mask to combine.

        Returns:
            str: The combined mask.
        """
        out = ''
        for i in range(len(mask1)):
            if mask1[i] == '.':
                out += mask2[i]
            else:
                out += mask1[i]

        return out
    
    def analyseSolves(self, numSolves: int = 100, displayAllTimes: bool = True, displayStats: bool = True) -> dict:
        """Repeatedly randomises and solves the cube, tracking various statistics about the solves.

        Args:
            numSolves (int, optional): The number of solves to perform. Defaults to 100.
            displayAllTimes (bool, optional): If True, prints the time taken and number of rotations for each solve. Defaults to True.
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
            self.randomiseCube()
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
                print(f'Time Taken : {round(yellowFaceTime - startTime,2)} seconds')
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
