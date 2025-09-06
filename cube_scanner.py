import cv2
import numpy as np
from tkinter import *
import imutils
from dominant_colour import getDominantColours
from cube import Cube

showCells = False
calibrationMode = False

USUAL_COLOUR_VALUES = {
    'Red': (0, 0, 255),
    'Green': (0, 255, 0),
    'Blue': (255, 0, 0),
    'Yellow': (0, 255, 255),
    'Orange': (0, 165, 255),
    'White': (255, 255, 255),
}

COLOURS = [
    ('Red', [109, 17, 20]),
    ('Green', [7, 108, 33]),
    ('Blue', [15, 37, 77]),
    ('Yellow', [149, 150, 50]),
    ('Orange', [203.5, 53, 33]),
    ('White', [133, 132, 132])
]

NEW_COLOUR = [
    ('Red', [115.84792873, 28.96458909, 15.96942809]),
    ('Green', [26.49611181, 99.89769382, 24.83975062]),
    ('Blue', [26.8278529, 36.01506922, 56.81930139]),
    ('Yellow', [149.99169571, 128.34543791, 17.32632797]),
    ('Orange', [198.48721967, 44.40870897, 10.94219687]),
    ('White', [128.6238628, 114.52529497, 97.18683709]),
]

def distance(r, g, b, r2, g2, b2) -> float:
    """
    Gets the distance between two RGB colors
    """
    return (r - r2)**2 + (g - g2)**2 + (b - b2)**2

def getClosestColourName(colour: tuple[float, float, float]) -> str:
    """
    Gets the name of the closest color to the given RGB values.
    """
    # Convert the RGB values to a tuple
    r, g, b = colour[0],colour[1],colour[2]

    # Find the closest color match
    closestColour = min(COLOURS, key=lambda x: distance(r, g, b, *x[1]))

    # Return the color name
    return closestColour[0]

def displayFace(image:np.ndarray,colourList:list[list]) -> np.ndarray:
    """
    Displays a map of all the faces of the cube which have been detected.
    """
    colourNames = ['White','Green','Red','Blue','Orange','Yellow']
    
    white = [420,20]
    diff = 72
    width = 21
    jump = 2

    colourValues = [white]
    yellow = [white[0],white[1] + 2 * (diff+jump)]
    for i in [-1,0,1,2]:
        colour = [white[0] + i*(diff+jump),white[1] + (diff+jump)]
        colourValues.append(colour.copy())

    colourValues.append(yellow)

    faceToPosition = dict(zip(colourNames,colourValues))

    topLeft = faceToPosition[colourList[4]]
    for i in range(3):
        for ii in range(3):
            cv2.rectangle(image,(topLeft[0] + i * width,topLeft[1] + ii * width), (topLeft[0] + (i+1) * (width)-jump,topLeft[1] + (ii+1) * (width)-jump),USUAL_COLOUR_VALUES[colourList[i+3*ii]],-1)

    return image

def extractColours(image:np.ndarray) -> list[list]:   
    """
    Extracts the colours of each cell in the Rubik's Cube face.
    """
    cells = []

    w,h = image.shape[:2]
    xInc = w//3
    yInc = h//3
    for y in range(3):
        for x in range(3):
            startX = int(round((x + 0.2) * xInc,0))
            startY = int(round((y + 0.2) * yInc,0))

            endX = int(round((x + 0.8) * xInc,0))
            endY = int(round((y + 0.8) * yInc,0))

            cells.append(image[startY:endY, startX:endX])

    counter = 0
    colours = []
    for cell in cells:
        counter += 1
        if showCells:
            cv2.namedWindow(f'cell {counter}',cv2.WINDOW_NORMAL)
            cv2.imshow(f'cell {counter}',cell.copy())

        dominantColour = getDominantColours(cell)[0]
        dominantColourName = getClosestColourName(dominantColour)

        colours.append(dominantColourName)
    return colours

def getFaces():
    previous3 = [[1],[2],[3]]
    previousFaces = {
        'Red': [],
        'Green': [],
        'Blue': [],
        'Yellow': [],
        'Orange': [],
        'White': [],
    }
    print("Starting camera...")
    vid = cv2.VideoCapture(0)
    
    if not vid.isOpened():
        print("Cannot open camera")
        raise Exception("Cannot open camera")
    
    while True:
        ret, frame = vid.read()

        framehsv = cv2.cvtColor(frame, cv2.COLOR_BGR2HSV)
        cv2.namedWindow('raw image', cv2.WINDOW_NORMAL)
        cv2.imshow('raw image',frame)

        blurred = cv2.cvtColor(frame,cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(blurred, (5, 5), cv2.BORDER_DEFAULT)

        canny = cv2.Canny(blurred, 20, 40)
        cv2.namedWindow('img',cv2.WINDOW_NORMAL)
        cv2.imshow('img',canny)

        kernel = np.ones((3,3), np.uint8)
        dilated = cv2.dilate(canny, kernel, iterations=2)
        cv2.namedWindow('img2',cv2.WINDOW_NORMAL)
        cv2.imshow('img2',dilated)

        contours = cv2.findContours(canny.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        contours = imutils.grab_contours(contours)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        puzzleContour = None
        output = frame.copy()
        cv2.namedWindow('Puzzle Outline',cv2.WINDOW_NORMAL)

        # loop over the contours
        counter = 20
        faceContours = []
        for c in contours:
            # approximate the contour
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.05 * peri, True)
            # if our approximated contour has four points, then we can
            # assume we have found the outline of the puzzle
            if 4 <= len(approx) <= 4 and 2200 > cv2.contourArea(approx) > 500:
                if ((approx[0][0][0] - approx[1][0][0]) ** 2 + (approx[0][0][1] - approx[1][0][1])**2)**0.5 * 2 < peri < 6 * ((approx[0][0][0] - approx[1][0][0]) ** 2 + (approx[0][0][1] - approx[1][0][1])**2)**0.5:               
                    puzzleContour = approx
                    counter -= 1
                    if counter == 0:
                        break
                    faceContours.append(approx)
                    cv2.drawContours(output, [puzzleContour], -1, (255, 0, 0), 5)

        if len(faceContours) > 4:
            medianArea = cv2.contourArea(faceContours[len(faceContours)//2])
            faceCornersX = []
            faceCornersY = []
            for i in range(len(faceContours)):
                if medianArea * 0.7 < cv2.contourArea(faceContours[i]) < 1.3 * medianArea:
                    for ii in range(4):
                        faceCornersX.append(faceContours[i][ii][0][0])
                        faceCornersY.append(faceContours[i][ii][0][1])

            areaRect = (max(faceCornersX) - min(faceCornersX)) * (max(faceCornersY) - min(faceCornersY))
            maxX, maxY = max(faceCornersX), max(faceCornersY)
            minX, minY = min(faceCornersX), min(faceCornersY)
            if areaRect * 0.62 < medianArea * 9 < areaRect * 1.4:
                if (max(faceCornersX) - min(faceCornersX)) * 0.8 < max(faceCornersY) - min(faceCornersY) < 1.2 * (max(faceCornersX) - min(faceCornersX)):
                    cv2.rectangle(output,(min(faceCornersX),min(faceCornersY)),(max(faceCornersX),max(faceCornersY)),(0,0,255),3)
        
                    normalOutput = frame.copy()
                    cv2.namedWindow('cropped',cv2.WINDOW_NORMAL)
                    cropped = normalOutput[minY:maxY,minX:maxX]
                    cv2.imshow("cropped", cropped)
        
                    colours = extractColours(cropped)

                    print(colours)
                    previous3.append(colours)

                    if previous3[-1] == previous3[-2] == previous3[-3]:
                        output = displayFace(output,previous3[-1])
                        previousFaces[colours[4]] = colours


        for colourName,colourRGB in previousFaces.items():
            if colourRGB != []:
                output = displayFace(output,colourRGB)
    
        cv2.imshow("Puzzle Outline", output)

        if cv2.waitKey(1) & 0xFF == ord('x'):
            break

    vid.release()
    cv2.destroyAllWindows()

    return previousFaces

def main():
    previousFaces = getFaces()
    cubeString = ''
    for face in  ['White','Green','Red','Blue','Orange','Yellow']:
        for colour in previousFaces[face]:
            cubeString += colour[0]

    cube = Cube(cubeString)
    print(cube)
    ax = cube.plot3D()

    while True:
        turn = input('Rotation: ')
        if turn == 'randomise':
            sequence = cube.randomiseCube()
            print(sequence)
            cube.displayCube() 
        elif turn == 'solve':
            cube.solve(ax)
            print(cube.movesMade)
        else:      
            cube.executeSequence(turn,True)
        ax = cube.plot3D(ax)

if __name__ == "__main__":
    main()