import cv2
import numpy as np

from .constants import FACE_TO_POSITION, USUAL_COLOUR_VALUES
from .dominant_colour import getDominantColours


def distance(r, g, b, r2, g2, b2) -> float:
    """Gets the distance between two RGB colors.

    Args:
        r (float): The red value of the first color.
        g (float): The green value of the first color.
        b (float): The blue value of the first color.
        r2 (float): The red value of the second color.
        g2 (float): The green value of the second color.
        b2 (float): The blue value of the second color.

    Returns:
        float: The distance between the two colors.
    """
    return (r - r2) ** 2 + (g - g2) ** 2 + (b - b2) ** 2


def getClosestColourName(colour: tuple[float, float, float], colours: list[tuple[str, np.ndarray]]) -> str:
    """Gets the name of the closest color to the given RGB values.

    Args:
        colour (tuple[float, float, float]): The RGB values of the color.

    Returns:
        str: The name of the closest color.
    """
    r, g, b = colour[0], colour[1], colour[2]

    closestColour = min(colours, key=lambda x: distance(r, g, b, *x[1]))

    return closestColour[0]


def displayFace(image: np.ndarray, colourList: list[list]) -> np.ndarray:
    """Displays a map of all the faces of the cube which have been detected.

    Args:
        image (np.ndarray): The image to draw the face on.
        colourList (list[list]): A list of lists containing the colours of each face of the cube.

    Returns:
        np.ndarray: The image with the face drawn on it.
    """

    # sizes of squares
    width = 21
    jump = 2

    # gets the topleft corner of the face and draws the squares in a 3x3 grid
    topLeft = FACE_TO_POSITION[colourList[4]]
    for i in range(3):
        for ii in range(3):
            cv2.rectangle(
                image,
                (topLeft[0] + i * width, topLeft[1] + ii * width),
                (topLeft[0] + (i + 1) * (width) - jump, topLeft[1] + (ii + 1) * (width) - jump),
                USUAL_COLOUR_VALUES[colourList[i + 3 * ii]],
                -1,
            )

    return image


def extractColours(image: np.ndarray, faceColours: list[tuple[str, np.ndarray]]) -> list[list]:
    """Extracts the colours of each cell in the Rubik's Cube face.

    Args:
        image (np.ndarray): The image of the Rubik's Cube face.

    Returns:
        list[list]: A list of lists containing the colours of each face of the cube.
    """
    cells = []

    w, h = image.shape[:2]
    xInc = w // 3
    yInc = h // 3
    for y in range(3):
        for x in range(3):
            startX = int(round((x + 0.2) * xInc, 0))
            startY = int(round((y + 0.2) * yInc, 0))

            endX = int(round((x + 0.8) * xInc, 0))
            endY = int(round((y + 0.8) * yInc, 0))

            cells.append(image[startY:endY, startX:endX])

    counter = 0
    colours = []
    for cell in cells:
        counter += 1
        dominantColour = getDominantColours(cell)[0]
        dominantColourName = getClosestColourName(dominantColour, faceColours)

        colours.append(dominantColourName)
    return colours


def filterContours(contours: list[np.ndarray], thresholdDistance: int) -> list[np.ndarray]:
    """Filters the detected contours to ensure they likely represent cube faces.

    Args:
        contours (list[np.ndarray]): The list of detected contours.
        thresholdDistance (int): The maximum distance from the average center to consider a contour valid.

    Returns:
        list[np.ndarray]: The filtered list of contours.
    """

    moments = [cv2.moments(contour) for contour in contours]
    centers = [(int(moment["m10"] / moment["m00"]), int(moment["m01"] / moment["m00"])) for moment in moments]
    (avgX, avgY) = np.mean(centers, axis=0)

    output = []
    for contour, (cx, cy) in zip(contours, centers):
        distance = np.sqrt((cx - avgX) ** 2 + (cy - avgY) ** 2)
        if distance < thresholdDistance:
            output.append(contour)

    return output


def bgr2rgb(col: np.ndarray) -> np.ndarray:
    """Convert a BGR tuple to an RGB tuple with values between 0 and 1.

    Args:
        col (tuple[int, int, int]): The BGR colour.

    Returns:
        tuple[float, float, float]: The RGB colour.
    """
    return np.array([col[2], col[1], col[0]])
