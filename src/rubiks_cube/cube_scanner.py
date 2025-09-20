from tkinter import *

import cv2
import numpy as np
from PIL import Image, ImageTk

from .constants import FACE_TO_POSITION, USUAL_COLOUR_VALUES
from .dominant_colour import getDominantColours

COLOURS = [
    ("Red", [205.27404537, 59.62644887, 44.40219895]),
    ("Green", [2.07276848e-01, 2.31331543e02, 1.56213033e02]),
    ("Blue", [6.98065468, 102.78523982, 188.25155498]),
    ("Yellow", [255, 255, 158.76374393]),
    ("Orange", [255, 162.99320226, 64.53646332]),
    ("White", [241.67310047, 254.99971655, 255]),
]


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


class CubeScanner:
    def __init__(self, videoLabel: Label, calibratedColours: dict[str, np.ndarray] = None) -> None:
        self.videoLabel = videoLabel
        self.vid = cv2.VideoCapture(0)
        self.previous3 = [[1], [2], [3]]
        self.previousFaces = {
            "Red": [],
            "Green": [],
            "Blue": [],
            "Yellow": [],
            "Orange": [],
            "White": [],
        }
        self.running = True
        self.photo = None

        if calibratedColours is not None:
            self.colours = []
            for colourName, rgb in calibratedColours.items():
                self.colours.append((colourName, rgb))
        else:
            self.colours = COLOURS

        self.updateFrame()

    def updateFrame(self) -> None:
        """Gets a frame from the VideoCapture and then tries to find a rubiks cube in
        the image, extract the colours and add it to the list of found faces."""
        if not self.running:
            if self.vid.isOpened():
                self.vid.release()
            return

        if not self.videoLabel.winfo_exists():
            self.running = False
            if self.vid.isOpened():
                self.vid.release()
            return

        ret, frame = self.vid.read()
        if not ret:
            if self.running:
                self.videoLabel.after(10, self.updateFrame)
            return

        grayed = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        blurred = cv2.GaussianBlur(grayed, (5, 5), cv2.BORDER_DEFAULT)
        canny = cv2.Canny(blurred, 20, 40)
        kernel = np.ones((3, 3), np.uint8)
        dilated = cv2.dilate(canny, kernel, iterations=2)
        dilatedFrame = dilated

        contours, _ = cv2.findContours(dilatedFrame.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)

        output = frame.copy()
        counter = 30
        faceContours = []
        totalWidth = 0
        for c in contours:
            peri = cv2.arcLength(c, True)
            approx = cv2.approxPolyDP(c, 0.05 * peri, True)
            minX, minY, width, height = cv2.boundingRect(approx)
            aspectRatio = width / height
            if len(approx) == 4 and 2000 > cv2.contourArea(approx) > 300 and 0.8 < aspectRatio < 1.2:
                counter -= 1
                if counter == 0:
                    break
                totalWidth += width
                faceContours.append(approx)

        if len(faceContours) > 0:
            faceContours = filterContours(faceContours, (totalWidth / len(faceContours)) * 4)

        if len(faceContours) > 4:
            avgArea = sum([cv2.contourArea(faceContours[i]) for i in range(len(faceContours))]) / len(faceContours)
            faceCornersX = []
            faceCornersY = []
            for i in range(len(faceContours)):
                if avgArea * 0.7 < cv2.contourArea(faceContours[i]) < 1.3 * avgArea:
                    for ii in range(4):
                        faceCornersX.append(faceContours[i][ii][0][0])
                        faceCornersY.append(faceContours[i][ii][0][1])

                    cv2.drawContours(output, [faceContours[i]], -1, (255, 0, 0), 5)

            if len(faceCornersX) >= 4 and len(faceCornersY) >= 4:
                areaRect = (max(faceCornersX) - min(faceCornersX)) * (max(faceCornersY) - min(faceCornersY))
                maxX, maxY = max(faceCornersX), max(faceCornersY)
                minX, minY = min(faceCornersX), min(faceCornersY)

                if areaRect * 0.45 < avgArea * 9 < areaRect * 1.1:
                    if (
                        (max(faceCornersX) - min(faceCornersX)) * 0.8
                        < max(faceCornersY) - min(faceCornersY)
                        < 1.2 * (max(faceCornersX) - min(faceCornersX))
                    ):
                        cv2.rectangle(
                            output,
                            (min(faceCornersX), min(faceCornersY)),
                            (max(faceCornersX), max(faceCornersY)),
                            (0, 0, 255),
                            3,
                        )
                        normalOutput = frame.copy()
                        cropped = normalOutput[minY:maxY, minX:maxX]
                        colours = extractColours(cropped, self.colours)
                        self.previous3.append(colours)
                        if self.previous3[-1] == self.previous3[-2] == self.previous3[-3]:
                            output = displayFace(output, self.previous3[-1])
                            self.previousFaces[colours[4]] = colours

        for _, colourRGB in self.previousFaces.items():
            if colourRGB != []:
                output = displayFace(output, colourRGB)

        w = round(self.videoLabel.winfo_width() * 0.9)
        h = round(self.videoLabel.winfo_height() * 0.9)
        if w <= 1 or h <= 1:
            h, w = output.shape[:2]

        frame_resized = cv2.resize(output, (w, h), interpolation=cv2.INTER_LINEAR)

        try:
            rgb_image = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
            pil_image = Image.fromarray(rgb_image)
            tk_image = ImageTk.PhotoImage(image=pil_image, master=self.videoLabel)

            # Keep a reference to prevent garbage collection
            self.photo = tk_image
            self.videoLabel.config(image=self.photo)

        except Exception as e:
            print(f"Error updating image: {e}")

        # Schedule next frame only if still running and label exists
        if self.running and self.videoLabel.winfo_exists():
            self.videoLabel.after(10, self.updateFrame)

    def stop(self) -> None:
        """Stops the webcam recording and releases the video."""
        self.running = False
        if hasattr(self, "vid") and self.vid.isOpened():
            self.vid.release()

    def getCubeString(self) -> str:
        """Returns the cube string representation of the scanned cube.

        Returns:
            str: The cube string representation, or an empty string if not all faces are scanned.
        """
        cubeString = ""
        for face in ["White", "Green", "Red", "Blue", "Orange", "Yellow"]:
            if self.previousFaces[face] == []:
                return ""
            for colour in self.previousFaces[face]:
                cubeString += colour[0]

        print(cubeString)

        return cubeString
