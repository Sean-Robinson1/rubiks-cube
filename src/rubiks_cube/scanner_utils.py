import logging

import cv2
import numpy as np

from .constants import FACE_TO_POSITION, USUAL_COLOUR_VALUES


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


def displayFace(image: np.ndarray, colourList: list[str]) -> np.ndarray:
    """Displays a map of all the faces of the cube which have been detected.

    Args:
        image (np.ndarray): The image to draw the face on.
        colourList (list[str]): The colour names of the face's nine squares.

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


def stickerColour(image: np.ndarray) -> tuple[float, float, float]:
    """The colour of one sticker cell, robust to glare and to a sliver of border or shadow.

    The pixels are split into a brighter and a darker group at the Otsu threshold and the median of the
    bigger group is taken. Glare only adds light so it lands in the bright group, border and shadow in
    the dark one. This replaced a 2-cluster kmeans that returned cluster 0 - the cluster order is
    random, so about half the time it read the glare. A plain median is fine until glare covers a good
    part of the cell (see the glare case in tests/scanner_images.py).

    Args:
        image (np.ndarray): The BGR cell image.

    Returns:
        tuple[float, float, float]: The sticker colour, RGB.
    """
    pixels = image.reshape(-1, 3)
    grey = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY).reshape(-1)
    threshold, _ = cv2.threshold(grey, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
    bright = grey > threshold
    group = pixels[bright] if bright.sum() * 2 > len(grey) else pixels[~bright]
    if len(group) == 0:
        group = pixels
    b, g, r = np.median(group, axis=0)
    return (float(r), float(g), float(b))


def extractCells(img: np.ndarray) -> list[np.ndarray]:
    """Extract the 9 cells from the given image of a cube face.

    Args:
        img (np.ndarray): The image of the cube face.

    Returns:
        list[np.ndarray]: A list of 9 images, each corresponding to a cell.
    """
    h, w = img.shape[:2]
    xInc = w // 3
    yInc = h // 3
    cells = []
    for y in range(3):
        for x in range(3):
            startX = int(round((x + 0.2) * xInc))
            startY = int(round((y + 0.2) * yInc))
            endX = int(round((x + 0.8) * xInc))
            endY = int(round((y + 0.8) * yInc))
            cells.append(img[startY:endY, startX:endX])
    return cells


def extractColours(image: np.ndarray, faceColours: list[tuple[str, np.ndarray]]) -> list[str]:
    """Extracts the colours of each cell in the Rubik's Cube face.

    Args:
        image (np.ndarray): The image of the Rubik's Cube face.

    Returns:
        list[str]: The colour name of each of the nine cells.
    """
    cells = extractCells(image)

    counter = 0
    colours = []
    for cell in cells:
        counter += 1
        dominantColourName = getClosestColourName(stickerColour(cell), faceColours)

        colours.append(dominantColourName)
    return colours


def filterContours(contours: list[np.ndarray], thresholdDistance: float) -> list[np.ndarray]:
    """Filters the detected contours to ensure they likely represent cube faces.

    Args:
        contours (list[np.ndarray]): The list of detected contours.
        thresholdDistance (float): The maximum distance from the average center to consider a contour valid.

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


def readFace(frame: np.ndarray, faceColours: list, output: np.ndarray | None = None) -> list[str] | None:
    """Looks for a cube face in a camera frame and reads its nine colours.

    Args:
        frame (np.ndarray): The BGR camera frame.
        faceColours (list): (name, rgb) pairs to classify the stickers against.
        output (np.ndarray, optional): If given, the found stickers and face are drawn onto it.

    Returns:
        list[str] | None: The colour name of each of the nine stickers, or None if no face was found.
    """
    # manipulating image to scan contours
    grayed = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    blurred = cv2.GaussianBlur(grayed, (5, 5), cv2.BORDER_DEFAULT)
    canny = cv2.Canny(blurred, 20, 40)
    kernel = np.ones((3, 3), np.uint8)
    dilated = cv2.dilate(canny, kernel, iterations=2)
    dilatedFrame = dilated

    contours, _ = cv2.findContours(dilatedFrame.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
    contours = sorted(contours, key=cv2.contourArea, reverse=True)

    counter = 30
    faceContours = []
    totalWidth = 0
    # filtering out non-square contours
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

    if len(faceContours) > 3:
        faceContours = filterContours(faceContours, (totalWidth / len(faceContours)) * 4)
        avgArea = sum([cv2.contourArea(faceContours[i]) for i in range(len(faceContours))]) / len(faceContours)

        faceCornersX = []
        faceCornersY = []
        for i in range(len(faceContours)):
            if avgArea * 0.7 < cv2.contourArea(faceContours[i]) < 1.3 * avgArea:
                for ii in range(4):
                    faceCornersX.append(faceContours[i][ii][0][0])
                    faceCornersY.append(faceContours[i][ii][0][1])

                if output is not None:
                    cv2.drawContours(output, [faceContours[i]], -1, (255, 0, 0), 5)

        # checking if there are enough corners to make a square
        if len(faceCornersX) > 4 and len(faceCornersY) > 4:
            maxX, maxY = max(faceCornersX), max(faceCornersY)
            minX, minY = min(faceCornersX), min(faceCornersY)

            areaRect = (maxX - minX) * (maxY - minY)

            if areaRect * 0.45 < avgArea * 9 < areaRect * 1.1:
                # checking if the rectangle is roughly square
                if (maxX - minX) * 0.8 < maxY - minY < 1.2 * (maxX - minX):
                    if output is not None:
                        cv2.rectangle(output, (minX, minY), (maxX, maxY), (0, 0, 255), 3)

                    cropped = frame[minY:maxY, minX:maxX]
                    colours = extractColours(cropped, faceColours)

                    logging.info(f"Detected colours: {colours}")

                    return colours
    return None
