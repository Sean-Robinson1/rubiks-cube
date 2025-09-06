import random
from cube_plotter import plotRubiks3D
from cube_utils import rotate, checkMask
import time
import pyperclip
import copy

SOLVED_MASK = 'WWWWWWWWWGGGGGGGGGRRRRRRRRRBBBBBBBBBOOOOOOOOOYYYYYYYYY'

class Cube:
    def __init__(self,info: str = None) -> None:
        #top = 0, left = 1, front = 2, right = 3, back = 4, bottom = 5
        #top = white, left = green, front = red, right = blue, back = orange, bottom = yellow
        self.sideNumToColour = {0:'W',1:'G',2:'R',3:'B',4:'O',5:'Y'}
        self.colourToSideNum = {'W':0,'G':1,'R':2,'B':3,'O':4,'Y':5}
        self.colours = ['W', 'G', 'R', 'B', 'O', 'Y']
        self.faces: list[list[str]] = []
        self.oppFaces = {0:5,1:3,2:4,3:1,4:3,5:0}
        self.calculateFaces('B','Y')
        if not info:
            for i in range(0,6):
                x = []
                for ii in range(3):
                    x.append([])
                    for _ in range(3):
                        x[ii].append(self.sideNumToColour[i])
                
                self.faces.append(x)
        else:
            counter = 0
            for i in range(0,6):
                x = []
                for ii in range(3):
                    x.append([])
                    for iii in range(3):
                        x[ii].append(info[counter])
                        counter += 1
                
                self.faces.append(x)

        self.movesMade = []

        self.ax = None

    def __str__(self) -> str:
        outputString = ''
        for face in range(6):
            for row in self.faces[face]:
                for square in row:
                    outputString += square
        return outputString
    
    def __getitem__(self,index: int) -> list[list[str]]:
        return self.faces[index]

    def calculateFaces(self, front:int, top:int) -> None:
        """
        Calculates faces relative to a chosen front face and a chosen top face.
        
        Note - this assumes the two faces are not opposites.
        """
        self.top = self.colourToSideNum[top]
        self.front = self.colourToSideNum[front]
        self.bottom = self.oppFaces[self.top]
        self.back = self.oppFaces[self.front]
        self.left = ((self.front - 2) % 4) + 1
        self.right = self.oppFaces[self.left]
    
    def getPlottingList(self) -> list[str]:
        """
        Returns a list of colours in the correct order to be plotted.
        """
        squareToColour = {'W':'White','Y':'Yellow','B':'Blue','G':'Green','R':'Red','O':'Orange'}
        outputList = []
        for face in [(0,-1,1),(5,1,1),(2,1,1),(4,1,-1),(1,1,-1),(3,1,1)]:
            for row in self.faces[face[0]][::face[1]]:
                for square in row[::face[2]]:
                    outputList.append(squareToColour[square])
        return outputList

    def displayCube(self,faces: list[list[str]] = None) -> None:
        """
        Displays the cube in the console.
        """
        if faces == None:
            faces = self.faces
        print('\n\n')
        colourToUnicode = {'W':'⬜','G':'🟩','R':'🟥','B':'🟦','O':'🟧','Y':'🟨'}
        errorChar = '❔'
        
        for row in faces[0]:
            print(10*' ',end='')
            for square in row:
                print(colourToUnicode.get(square,errorChar),end=' ')
            print()

        for row in range(3):
            for faceIndex in range(1,5):
                face = faces[faceIndex]

                for square in face[row]:
                    print(colourToUnicode.get(square,errorChar),end=' ')
                print(' ',end='')
            print()

        for row in faces[5]:
            print(10*' ',end='')
            for square in row:
                print(colourToUnicode.get(square,errorChar),end=' ')
            print()

    def randomiseCube(self) -> list[str]:
        """
        Randomises the cube to a valid state.
        """
        turns = ['R','L','U','D','F','B']
        sequence = []
        for _ in range(50):
            move = turns[random.randint(0,5)]

            if random.random() > 0.5:
                move += 'i'

            sequence.append(move)
        
        self.executeSequence(''.join(sequence))
        pyperclip.copy(str(sequence))
        return sequence
    
    def workBackwards(self,sequence: list[str]):
        """
        Given the sequence of moves that scrambled/randomised the cube, this
        function will work backwards and solve the cube. This method is often
        used to fake solving the cube, specifically cubes of much larger sizes.
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

    def rotateU(self,direction:int = 0) -> None:
        """
        Performs a rotation of the upper face.
        """
        if direction == 0:
            self.faces[4][0],self.faces[1][0],self.faces[2][0],self.faces[3][0] = self.faces[1][0],self.faces[2][0],self.faces[3][0],self.faces[4][0]
            self.rotateFace(0)
        else:
            self.faces[1][0],self.faces[2][0],self.faces[3][0],self.faces[4][0] = self.faces[4][0],self.faces[1][0],self.faces[2][0],self.faces[3][0]
            self.rotateFace(0,-1)

    def rotateD(self,direction:int = 0) -> None:
        """
        Performs a rotation of the down face.
        """
        if direction == 0:
            self.faces[1][2],self.faces[2][2],self.faces[3][2],self.faces[4][2] = self.faces[4][2],self.faces[1][2],self.faces[2][2],self.faces[3][2]  
            self.rotateFace(5)
        else:
            self.faces[4][2],self.faces[1][2],self.faces[2][2],self.faces[3][2] = self.faces[1][2],self.faces[2][2],self.faces[3][2],self.faces[4][2]
            self.rotateFace(5,-1)

    def rotateF(self,direction:int = 0) -> None:
        """
        Performs a rotation of the front face.
        """
        if direction == 0:
            self.rotateFace(2)

            for i in range(3):
                self.faces[1][2-i][2], self.faces[0][2][i], self.faces[3][i][0], self.faces[5][0][2-i] = self.faces[5][0][2-i], self.faces[1][2-i][2], self.faces[0][2][i], self.faces[3][i][0]

        else:
            self.rotateFace(2,-1)

            for i in range(3):
                self.faces[1][2-i][2], self.faces[0][2][i], self.faces[3][i][0], self.faces[5][0][2-i] = self.faces[0][2][i], self.faces[3][i][0], self.faces[5][0][2-i], self.faces[1][2-i][2]

    def rotateB(self,direction:int = 0) -> None:
        """
        Performs a rotation of the back face.
        """
        if direction == 0:
            self.rotateFace(4)
            for i in range(3):
                self.faces[1][2-i][0], self.faces[0][0][i], self.faces[3][i][2], self.faces[5][2][2-i] = self.faces[0][0][i], self.faces[3][i][2], self.faces[5][2][2-i], self.faces[1][2-i][0]
           
        else:
            self.rotateFace(4,-1)
            for i in range(3):
                self.faces[1][2-i][0], self.faces[0][0][i], self.faces[3][i][2], self.faces[5][2][2-i] = self.faces[5][2][2-i], self.faces[1][2-i][0], self.faces[0][0][i], self.faces[3][i][2]

    def rotateR(self,direction:int = 0) -> None:
        """
        Performs a rotation of the right face.
        """
        if direction == 0:
            self.rotateFace(3)
            for i in range(3):
                self.faces[2][2-i][2], self.faces[0][2-i][2], self.faces[4][i][0], self.faces[5][2-i][2] = self.faces[5][2-i][2], self.faces[2][2-i][2], self.faces[0][2-i][2], self.faces[4][i][0]
           
        else:
            self.rotateFace(3,-1)
            for i in range(3):
                self.faces[2][2-i][2], self.faces[0][2-i][2], self.faces[4][i][0], self.faces[5][2-i][2] = self.faces[0][2-i][2], self.faces[4][i][0], self.faces[5][2-i][2], self.faces[2][2-i][2]   

    def rotateL(self,direction:int = 0) -> None:
        """
        Performs a rotation of the left face.
        """
        if direction == 0:
            self.rotateFace(1)
            for i in range(3):
                self.faces[2][2-i][0], self.faces[0][2-i][0], self.faces[4][i][2], self.faces[5][2-i][0] = self.faces[0][2-i][0], self.faces[4][i][2], self.faces[5][2-i][0], self.faces[2][2-i][0]

        else:
            self.rotateFace(1,-1)

            for i in range(3):
                self.faces[2][2-i][0], self.faces[0][2-i][0], self.faces[4][i][2], self.faces[5][2-i][0] = self.faces[5][2-i][0], self.faces[2][2-i][0], self.faces[0][2-i][0], self.faces[4][i][2]

    def rotateFace(self,face:int = 2, direction:int =0) -> None:
        """
        Rotates the specified face of the cube 90 degrees clockwise or anti-clockwise.
        """
        squares = []
        if direction == 0:
            for square in [0,1,2,5,8,7,6,3]:
                column = square % 3
                row = square // 3

                squares.append(self.faces[face][row][column])

            for squareIndex in range(len([2,5,8,7,6,3,0,1])):
                square = [2,5,8,7,6,3,0,1][squareIndex]
                column = square % 3
                row = square // 3

                self.faces[face][row][column] = squares[(squareIndex)]

        else:
            for square in [0,1,2,5,8,7,6,3]:
                column = square % 3
                row = square // 3

                squares.append(self.faces[face][row][column])

            for squareIndex in range(len([6,3,0,1,2,5,8,7])):
                square = [6,3,0,1,2,5,8,7][squareIndex]
                column = square % 3
                row = square // 3

                self.faces[face][row][column] = squares[(squareIndex)]

    def executeSequence(self,sequence: str, useColours: bool = False) -> None:
        """
        Executes a sequence of moves on the Rubik's Cube.
        """
        sequence = sequence.replace(' ','')
        if not useColours:
            sequence += ' '
            letterToFunc = {'R':self.rotateR,'L':self.rotateL,'U':self.rotateU,'D':self.rotateD,'F':self.rotateF,'B':self.rotateB}
            counter = 0
            while counter < len(sequence)-1:
                movement = sequence[counter]
                moveStr = movement
                direction = 0
                numMoves = 1
                if sequence[counter + 1] == "'" or sequence[counter + 1] == 'i':
                    direction = -1
                    counter += 1
                    moveStr += 'i'
                elif num := sequence[counter + 1].isdigit() == True:
                    numMoves = num
                    counter += 1
                    for _ in range(numMoves - 1):
                        self.movesMade.append(movement)
                counter += 1
                self.movesMade.append(moveStr)
                for _ in range(numMoves):
                    letterToFunc[movement](direction)  
        else:
            sequence += ' '
            letterToFunc = {'B':self.rotateR,'G':self.rotateL,'W':self.rotateU,'Y':self.rotateD,'R':self.rotateF,'O':self.rotateB}
            counter = 0
            while counter < len(sequence)-1:
                movement = sequence[counter]
                direction = 0
                numMoves = 1
                
                if sequence[counter + 1] == "'" or sequence[counter + 1] == 'i':
                    direction = -1
                    counter += 1
                elif sequence[counter + 1].isdigit() == True:
                    numMoves = 2
                    counter += 1
                counter += 1

                for _ in range(numMoves):
                    letterToFunc[movement](direction)

    def checkMask(self,mask: str) -> bool:
        """
        Checks if the cube matches a mask pattern.
        """
        stringVersion = str(self)
        for i in range(len(mask)):
            if mask[i] != '.' and mask[i] != stringVersion[i]:
                return False
        return True

    def plot3D(self) -> None:
        """
        Plots the cube in 3D.
        """
        self.ax = plotRubiks3D(self.getPlottingList(),self.ax)

    def getOppositeFace(self,colour: str) -> str:
        """Returns the opposite face relative to the given face colour"""
        mapping = {'R': 'O', 'B': 'G', 'W': 'Y'}
        return mapping.get(colour, None)

    def getLeftFace(self, colour: str) -> str:
        """Returns the left face relative to the given face colour."""
        mapping = {'R': 'G', 'B': 'R', 'O': 'B', 'G': 'O'}
        return mapping.get(colour, None)

    def getRightFace(self, colour: str) -> str:
        """Returns the right face relative to the given face colour."""
        mapping = {'R': 'B', 'B': 'O', 'O': 'G', 'G': 'R'}
        return mapping.get(colour, None)
    
    def convertSequenceFromFace(self,face: str,sequence: str) -> None:
        """
        Converts a sequence of moves from the perspective of a given face.
        """
        out = ''
        mapper = {'B':{'F':'R','R':'B','B':'L','L':'F'},'G':{'F':'L','R':'F','B':'R','L':'B'},'O':{'F':'B','R':'L','B':'F','L':'R'}}
        for letter in sequence:
            out += mapper.get(face,{}).get(letter,letter) 

        self.executeSequence(out)

    def solve(self) -> None:
        """
        Solves the Rubik's Cube.
        """
        self.movesMade = []
        self.solveCross()
        self.solveF2LCorners()
        self.solveF2LMiddlePieces()
        self.solveYellowCross()
        self.alignYellowEdges()
        self.solveYellowCorners()
        self.final()

    def solveCross(self) -> None:
        """
        Gets the white cross on the top of the cube.
        """
        # solved masks for each white center piece for each face
        solvedMasks = {('G','...WW.....G..G........................................'),
                       ('R','....W..W...........R..R...............................'),
                       ('B','....WW......................B..B......................'),
                       ('O','.W..W................................O..O.............')}

        masksWithMoves = {('G', '...GW.....W..G........................................', "FU'RU"),
                          ('G', '....W........G..W...............................G.....', "F'U'RU"),
                          ('R', '....W..R...........W..R...............................', "FU'RU"),
                          ('R', '....W.................R..W....................R.......', "F'U'RU"),
                          ('B', '....WB......................W..B......................', "FU'RU"),
                          ('B', '....W..........................B..W...............B...', "F'U'RU"),
                          ('O', '.O..W................................W..O.............', "FU'RU"),
                          ('O', '....W...................................O..W........O.', "F'U'RU")
        }

        recurseMasks = {'...WW.....G..G........................................',
                        '....W..W...........R..R...............................',
                        '....WW......................B..B......................',
                        '.W..W................................O..O.............',
                        '...GW.....W..G........................................',
                        '....W..R...........W..R...............................',
                        '....WB......................W..B......................',
                        '.O..W................................W..O.............',
                        '....W..........................B..W...............B...',
                        '....W........G..W...............................G.....',
                        '....W.................R..W....................R.......',
                        '....W...................................O..W........O.'
                        }

        
        numCorrect = 0
        removed = "." * 54
        while numCorrect != 4:
            toRemove = []
            for face, mask, pattern in masksWithMoves:
                if self.checkMask(mask):
                    toRemove.append((face,mask,pattern))
                    recurseMasks.discard(mask)
                    self.convertSequenceFromFace(face,pattern)

            for item in toRemove:
                masksWithMoves.remove(item)

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
                masksWithMoves = set(map(lambda x : (x[0],self.combineMasks(x[1],removed),x[2]),masksWithMoves))

            recurseMasks = set(filter(lambda x : not self.checkMask(x), recurseMasks))

            moves = self.recurseToMasks(recurseMasks,5) 

            if moves is None:
                for face, mask in solvedMasks:
                    if not self.checkMask(mask):
                        self.convertSequenceFromFace(face,"FU'RU")
                        
            if moves is not None:
                self.executeSequence("".join(moves))

    def solveF2LCorners(self) -> None:
        """
        Solves all white corner pieces as part of the F2L (First 2 Layers) solution.
        """

        solvedMasks =  {('R','.W.WWW.WW.G..G.....RR.R....BB..B.....O..O.............'),
                        ('B','.WWWWW.W..G..G.....R..R.....BB.B....OO..O.............'),
                        ('O','WW.WWW.W.GG..G.....R..R.....B..B.....OO.O.............'),
                        ('G','.W.WWWWW..GG.G....RR..R.....B..B.....O..O.............')}

        insertionMasks = {('RB1','.W.WWW.W..G..G.....R..R...B.B..B.R...O..O......W......'),
                          ('RB2','.W.WWW.W..G..G.....R..R...R.B..B.W...O..O......B......'),
                          ('RB3','.W.WWW.W..G..G.....R..R...W.B..B.B...O..O......R......'),
                          ('BO1','.W.WWW.W..G..G.....R..R.....B..B...O.O..O.B..........W'),
                          ('BO2','.W.WWW.W..G..G.....R..R.....B..B...B.O..O.W..........O'),
                          ('BO3','.W.WWW.W..G..G.....R..R.....B..B...W.O..O.O..........B'),
                          ('OG1','.W.WWW.W..G..G.O...R..R.....B..B.....O..O...G......W..'),
                          ('OG2','.W.WWW.W..G..G.W...R..R.....B..B.....O..O...O......G..'),
                          ('OG3','.W.WWW.W..G..G.G...R..R.....B..B.....O..O...W......O..'),
                          ('GR1','.W.WWW.W..G..G...R.R..R.G...B..B.....O..O....W........'),
                          ('GR2','.W.WWW.W..G..G...G.R..R.W...B..B.....O..O....R........'),
                          ('GR3','.W.WWW.W..G..G...W.R..R.R...B..B.....O..O....G........')}
        
        correctPieces = 0
        while correctPieces != 4:
            correctPieces = 0
            for mask in solvedMasks:
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
                for face, mask in solvedMasks:
                    if not self.checkMask(mask):
                        self.insertCorner(face+"_2")
                        break
            else:
                self.executeSequence("".join(moves))

            for mask in insertionMasks:
                if self.checkMask(mask[1]):
                    self.insertCorner(mask[0])

    def insertCorner(self,code: str) -> None:
        """
        Inserts a corner piece correctly as part of the F2L (First 2 Layers) solution.
        """
        face = code[0]
        insertionMethod = int(code[2])
        if insertionMethod == 1:
            self.convertSequenceFromFace(face,"FLDDL'F'")
        elif insertionMethod == 2:
            self.convertSequenceFromFace(face,"R'D'R")
        elif insertionMethod == 3:
            self.convertSequenceFromFace(face,"FDF'")

    def solveF2LMiddlePieces(self) -> None:
        """
        Inserts the middle layer edge pieces correctly as part of the F2L (First 2 Layers) solution.
        """
        mask = 'WWWWWWWWWGGG.G....RRR.R....BBB.B....OOO.O.............'

        ## solved masks

        redBlue      = ('RB','WWWWWWWWWGGG.G....RRR.RR...BBBBB....OOO.O.............')
        redGreen     = ('RG','WWWWWWWWWGGG.GG...RRRRR....BBB.B....OOO.O.............')
        blueOrange   = ('BO','WWWWWWWWWGGG.G....RRR.R....BBB.BB...OOOOO.............')
        orangeGreen  = ('OG','WWWWWWWWWGGGGG....RRR.R....BBB.B....OOO.OO............')

        solvedMasks = {redBlue,redGreen,blueOrange,orangeGreen}

        ## positions for insertion

        redBlue      = ('RB','WWWWWWWWWGGG.G....RRR.R..R.BBB.B....OOO.O.....B.......')
        redGreen     = ('RG','WWWWWWWWWGGG.G....RRR.R..R.BBB.B....OOO.O.....G.......')
        blueRed      = ('BR','WWWWWWWWWGGG.G....RRR.R....BBB.B..B.OOO.O.........R...')
        blueOrange   = ('BO','WWWWWWWWWGGG.G....RRR.R....BBB.B..B.OOO.O.........O...')
        orangeBlue   = ('OB','WWWWWWWWWGGG.G....RRR.R....BBB.B....OOO.O..O........B.')
        orangeGreen  = ('OG','WWWWWWWWWGGG.G....RRR.R....BBB.B....OOO.O..O........G.')
        greenOrange  = ('GO','WWWWWWWWWGGG.G..G.RRR.R....BBB.B....OOO.O.......O.....')
        greenRed     = ('GR','WWWWWWWWWGGG.G..G.RRR.R....BBB.B....OOO.O.......R.....')

        possibleMasks = {redBlue,redGreen,blueRed,blueOrange,orangeBlue,orangeGreen,greenOrange,greenRed}

        correctPieces = 0
        while correctPieces != 4:
            correctPieces = 0
            for mask in solvedMasks:
                if self.checkMask(mask[1]):
                    filtered = filter(lambda x: sorted(x[0]) != sorted(mask[0]),possibleMasks)
                    possibleMasks = list(map(lambda a: (a[0],self.combineMasks(a[1],mask[1])),filtered))
                    correctPieces += 1

            if correctPieces == 4:
                break
            
            inserted = False
            for mask in possibleMasks:
                if self.checkMask(mask[1]):
                    self.insertPiece(mask[0])
                    inserted = True

            if inserted:
                continue

            recurseMasks = list(map(lambda x: x[1],possibleMasks))
            moves = self.recurseToMasks(recurseMasks,2)

            if moves is None:
                for face, mask in solvedMasks:
                    if not self.checkMask(mask):
                        self.insertPiece(face)
                        break
            else:
                self.executeSequence("".join(moves))

            for mask in possibleMasks:
                if self.checkMask(mask[1]):
                    self.insertPiece(mask[0])

    def solveYellowCross(self) -> None:
        """
        Solves the yellow cross.
        """
        desiredMask = 'WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO....Y.YYY.Y.'

        alg = "FLDL'D'F'"

        yellowLMasks = {('O','WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO....Y.YY....'),
                        ('G','WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO....Y..YY...'),
                        ('B','WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO......YY..Y.'),    
                        ('R','WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO.......YY.Y.')        
        }

        yellowLineMasks = {('R','WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO......YYY...'),
                           ('B','WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO....Y..Y..Y.'),    
        }

        while not self.checkMask(desiredMask):
            executed = False
            for face,mask in yellowLMasks:
                if self.checkMask(mask):
                    self.convertSequenceFromFace(face,alg) 
                    executed = True
                    break

            for face,mask in yellowLineMasks:
                if self.checkMask(mask):
                    self.convertSequenceFromFace(face,alg) 
                    executed = True
                    break
            
            if not executed and self.checkMask('WWWWWWWWWGGGGGG...RRRRRR...BBBBBB...OOOOOO.......Y....'):
                self.executeSequence(alg)

    def alignYellowEdges(self) -> None:
        """
        Aligns the yellow edges so the corners can be inserted.
        """
        while not self.checkMask('WWWWWWWWWGGGGGG.G.RRRRRR.R.BBBBBB.B.OOOOOO.O..Y.YYY.Y.'):
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
                    self.convertSequenceFromFace(face1, "D L D L' D L DD L' D")
                    self.convertSequenceFromFace(self.getLeftFace(face1),"L D L' D L DD L' D")
                else:
                    if self.getLeftFace(face1) == face2:
                        self.convertSequenceFromFace(face2, "L D L' D L DD L' D")
                    else:
                        self.convertSequenceFromFace(face1, "L D L' D L DD L' D")
            else:
                self.executeSequence('D')

    def checkValidCorners(self) -> list[str]:
        """
        Checks how many of the 4 corners for the yellow face are in the correct position.
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
        """
        Correctly orients the yellow corners.
        """
        validCorners = self.checkValidCorners()

        if len(validCorners) == 4:
            return 
        
        elif len(validCorners) == 0:
            self.executeSequence("DLD'R'DL'D'R")
            self.solveYellowCorners()

        else:
            for _ in range(3):
                self.convertSequenceFromFace(validCorners[0],"DLD'R'DL'D'R")
                if len(self.checkValidCorners()) == 4:
                    return
            self.solveYellowCorners()

    def final(self) -> None:
        """
        Finalizes the solution by orienting the last layer.
        """
        while not self.checkMask(SOLVED_MASK):
            if self.faces[5][0][0] != 'Y':
                while self.faces[5][0][0] != 'Y':
                    self.executeSequence("L' U' L U")
            self.executeSequence("D")

    def insertPiece(self, code: str) -> None:
        """
        Correctly inserts a piece into the middle layer.
        """
        face = code[0]
        otherFace = code[1]

        if otherFace == self.getLeftFace(face):
            self.convertSequenceFromFace(face, "DLD'L'D'F'DF")    
        else:
            self.convertSequenceFromFace(face, "D'R'DRDFD'F'")
    
    def recurseToMasks(self, masks: list[str], depth: int = 6) -> list[str] | None:
        """
        Calls a function to perform BFS until a solution is found or the maximum depth is reached.
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
        """
        Performs BFS until a solution is found or the maximum depth is reached. Has some optimisations.
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
        
        moves = ["D","U","F","L","R","B","D'","U'","F'","L'","R'","B'"]

        for move in range(12):
            newstate = rotate(state,moves[move])
            result = self.findMasksRecursion(masks,depth-1,newstate,cache) 

            if result is not None:
                cache[cache_key] = [moves[move]] + result
                return cache[cache_key]
        
        return None
    
    def showMask(self, mask: str) -> None:
        """
        Takes a mask and displays it in the terminal in a clear and easy to read way.
        This was used mainly for debugging the code and checking the masks I made
        were valid.
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
        """
        Combines two masks. If they both specify a certain sqaure differently,
        priority will be given to mask1, and the output mask will take the value
        mask1 assigns to that square.
        """
        out = ''
        for i in range(len(mask1)):
            if mask1[i] == '.':
                out += mask2[i]
            else:
                out += mask1[i]

        return out

    def optimiseMoves(self,moves: list[str]) -> list[str]:
        """
        Looks through a list of moves and applies general rules to reduce the 
        total number of rotations while maintaining the same output. i.e. running
        this function will result in a shorter list of moves that will perform
        the same transformation on the cube.        
        """
        ## checking if there is a repeated section of 4
        newList = []
        i = 0
        while i <= len(moves) - 4:
            if moves[i] == moves[i+1] == moves[i+2] == moves[i+3]:
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
            if moves[i] == moves[i+1] == moves[i+2]:
                if len(moves[i]) == 1:
                    newList.append(moves[i] + 'i')
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
        skippedLast = False
        while i < len(moves) -1:
            if moves[i][0] == moves[i+1][0] and moves[i] != moves[i+1]:
                i += 2
                skippedLast = False
            else:
                newList.append(moves[i])
                i += 1
                skippedLast = True

        if skippedLast:
            newList.append(moves[-1])

        return newList

def main() -> None:
    cube = Cube()
    cube.plot3D()

    cube.ax.view_init(elev = 210,azim = 120)

    while True:
        turn = input('Rotation: ')
        if turn == 'randomise' or turn == 'rand':
            sequence = cube.randomiseCube()
            print(" ".join(sequence))
            print(" ".join(sequence).replace("i","'"))
            cube.displayCube() 
        elif turn == 'solve':
            cube.movesMade = []
            cube.displayCube()
            startTime = time.time()
            cube.solveCross()
            whiteCrossTime = time.time()
            cube.displayCube()
            cube.solveF2LCorners()
            f2lCornersTime = time.time()
            cube.displayCube()
            cube.solveF2LMiddlePieces()
            f2lMiddlePiecesTime = time.time()
            cube.displayCube()
            cube.solveYellowCross()
            yellowCrossTime = time.time()
            cube.displayCube()
            cube.alignYellowEdges()
            cube.solveYellowCorners()
            cube.final()
            yellowFaceTime = time.time()
            cube.displayCube()
            
            print(f"Moves : {' '.join(cube.movesMade)}")
            print(f"Number of Rotations: {len(cube.movesMade)}")

            optimisedMoves = cube.optimiseMoves(cube.movesMade.copy())

            print(f"Moves : {' '.join(optimisedMoves)}")
            print(f"Number of Rotations: {len(optimisedMoves)}")
            print(f'Optimised {len(cube.movesMade) - len(optimisedMoves)} moves')

            print(f'\n-----------------------------')
            print(f'Time Taken : {round(yellowFaceTime - startTime,2)} seconds')

            print(f'White Cross:    {round(whiteCrossTime - startTime,2)} seconds')
            print(f'White Corners:  {round(f2lCornersTime - whiteCrossTime,2)} seconds')
            print(f'Middle Pieces:  {round(f2lMiddlePiecesTime - f2lCornersTime,2)} seconds')
            print(f'Yellow Cross:   {round(yellowCrossTime - f2lMiddlePiecesTime,2)} seconds')
            print(f'Yellow Face:    {round(yellowFaceTime - yellowCrossTime,2)} seconds')
            print(f'-----------------------------\n')

            cube.plot3D()
        elif turn == 'display':
            cube.displayCube()
        elif turn == 'mask':
            mask = input("Mask: ")
            print(cube.checkMask(mask))
        elif turn == 'print':
            print(cube)
        elif turn == 'masks':
            mask = input()
            cube.showMask(mask)
        elif turn == 'middles':
            cube.solveF2LMiddlePieces()
        elif turn == 'yellow':
            cube.solveYellowCross()
        elif turn == 'yellow edges' or turn == 'ye':
            cube.alignYellowEdges()
        elif turn == 'yellow corners' or turn == 'yc':
            cube.solveYellowCorners()
        elif turn == 'final':
            cube.final()
        elif turn == 'corners':
            cube.solveF2LCorners()
        elif turn == 'cross':
            cube.solveCross()
        elif turn == 'analyse':
            numSolves = int(input('Num Solves:  '))
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
            for i in range(numSolves):
                cube.randomiseCube()
                cube.movesMade = []
                startTime = time.time()
                cube.solveCross()
                totalCrossTime += time.time() - startTime
                crossTime = time.time()
                maxCrossTime = max(maxCrossTime, crossTime - startTime)
                cube.solveF2LCorners()
                totalCornersTime += time.time() - crossTime
                cornersTime = time.time()
                maxCornersTime = max(maxCornersTime, cornersTime - crossTime)
                cube.solveF2LMiddlePieces()
                totalMiddlesTime += time.time() - cornersTime
                middlesTime = time.time()
                maxMiddlesTime = max(maxMiddlesTime, middlesTime - cornersTime)
                cube.solveYellowCross()
                totalYellowCrossTime += time.time() - middlesTime
                yellowCrossTime = time.time()
                maxYellowCrossTime = max(maxYellowCrossTime, yellowCrossTime - middlesTime)
                cube.alignYellowEdges()
                totalYellowCrossTime += time.time() - yellowCrossTime
                yellowEdgesTime = time.time()
                maxYellowEdgesTime = max(maxYellowEdgesTime, yellowEdgesTime - yellowCrossTime)
                cube.solveYellowCorners()
                totalYellowEdgesTime += time.time() - yellowEdgesTime
                yellowEdgesTime = time.time()
                maxYellowEdgesTime = max(maxYellowEdgesTime, yellowEdgesTime - yellowEdgesTime)
                cube.final()
                totalFinalTime += time.time() - yellowEdgesTime
                yellowFaceTime = time.time()
                maxFinalTime = max(maxFinalTime, yellowFaceTime - yellowEdgesTime)

                totalTime += yellowFaceTime - startTime
                
                print(f'Time Taken : {round(yellowFaceTime - startTime,2)} seconds')
                optimisedMoves = cube.optimiseMoves(cube.movesMade.copy())
                print(f"Number of Rotations: {len(optimisedMoves)}")
                totalMoves += len(cube.movesMade)
                totalMovesOptimised += len(optimisedMoves)

            print(f"\n-----------------------------")
            print(f"Avg Cross Time: {round(totalCrossTime / numSolves,5)}")
            print(f"Avg Corners Time: {round(totalCornersTime / numSolves,5)}")
            print(f"Avg Middles Time: {round(totalMiddlesTime / numSolves,5)}")
            print(f"Avg Yellow Cross Time: {round(totalYellowCrossTime / numSolves,5)}")
            print(f"Avg Yellow Edges Time: {round(totalYellowEdgesTime / numSolves,5)}")
            print(f"Avg Final Time: {round(totalFinalTime / numSolves,5)}")
            print(f"-----------------------------")

            print(f"-----------------------------")
            print(f"Max Cross Time: {round(maxCrossTime,5)}")
            print(f"Max Corners Time: {round(maxCornersTime,5)}")
            print(f"Max Middles Time: {round(maxMiddlesTime,5)}")
            print(f"Max Yellow Cross Time: {round(maxYellowCrossTime,5)}")
            print(f"Max Yellow Edges Time: {round(maxYellowEdgesTime,5)}")
            print(f"Max Final Time: {round(maxFinalTime,5)}")
            print(f"-----------------------------")

            print(f"Average Time: {round(totalTime / numSolves,5)}")
            print(f"Avg number of Rotations: {round(totalMoves / numSolves, 5)}")
            print(f"Avg number of optimised rotations: {round(totalMovesOptimised / numSolves, 5)}")
            print(f"Avg number of rotations saved:  {round((totalMoves - totalMovesOptimised) / numSolves,2)}")
        else:      
            cube.executeSequence(turn,False)
        cube.plot3D()

if __name__ == "__main__":
    main()