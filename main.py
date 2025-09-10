from cube import Cube 
from gui import GUI
import time

def main() -> None:
    cube = Cube()
    gui = GUI(cube)
    gui.createTkWindow()

    while True:
        turn = input('Operation: ')
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

            optimisedMoves = cube.optimisedMoves

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

            gui.plot3D()
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
            cube.analyseSolves(numSolves)
        else:
            cube.executeSequence(turn, False)
        gui.plot3D()

if __name__ == "__main__":
    main()