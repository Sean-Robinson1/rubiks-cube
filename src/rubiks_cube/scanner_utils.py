import logging
from collections.abc import Sequence

import cv2
import numpy as np

from .constants import FACE_TO_POSITION, PLOTTING_COLOUR_MAP, SOLVED_MASK
from .cube_validation import CENTRES, validateCube


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


def displayFace(image: np.ndarray, face: str, colours: Sequence[Sequence[float]]) -> np.ndarray:
    """Draws one face into the map of scanned faces.

    Args:
        image (np.ndarray): The image to draw the face on.
        face (str): The face's letter, which decides where it goes on the map.
        colours (Sequence[Sequence[float]]): The BGR colours of the face's nine squares.

    Returns:
        np.ndarray: The image with the face drawn on it.
    """

    # sizes of squares
    width = 21
    jump = 2

    # gets the topleft corner of the face and draws the squares in a 3x3 grid
    topLeft = FACE_TO_POSITION[PLOTTING_COLOUR_MAP[face]]
    for i in range(3):
        for ii in range(3):
            cv2.rectangle(
                image,
                (topLeft[0] + i * width, topLeft[1] + ii * width),
                (topLeft[0] + (i + 1) * (width) - jump, topLeft[1] + (ii + 1) * (width) - jump),
                tuple(int(c) for c in colours[i + 3 * ii]),
                -1,
            )

    return image


def stickerColour(image: np.ndarray) -> tuple[float, float, float]:
    """The colour of one sticker cell, robust to glare and to a sliver of border or shadow.

    The pixels are split into a brighter and a darker group at the Otsu threshold and the median of the
    bigger group is taken. Glare only adds light so it lands in the bright group, border and shadow in
    the dark one.

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
    """Looks for a cube face in a camera frame and names its nine colours against fixed references.

    Args:
        frame (np.ndarray): The BGR camera frame.
        faceColours (list): (name, rgb) pairs to classify the stickers against.
        output (np.ndarray, optional): If given, the found stickers and face are drawn onto it.

    Returns:
        list[str] | None: The colour name of each of the nine stickers, or None if no face was found.
    """
    measured = readFaceColours(frame, output)
    if measured is None:
        return None
    colours = [getClosestColourName(colour, faceColours) for colour in measured]
    logging.info(f"Detected colours: {colours}")
    return colours


def readFaceColours(frame: np.ndarray, output: np.ndarray | None = None) -> list[tuple[float, float, float]] | None:
    """Looks for a cube face in a camera frame and measures its nine sticker colours, without naming them.

    Args:
        frame (np.ndarray): The BGR camera frame.
        output (np.ndarray, optional): If given, the found stickers and face are drawn onto it.

    Returns:
        list[tuple[float, float, float]] | None: Each sticker's RGB colour, or None if no face was found.
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
                    return [stickerColour(cell) for cell in extractCells(cropped)]
    return None


def toLab(colours: Sequence[Sequence[float]]) -> np.ndarray:
    """RGB colours to LAB, where distances match how different colours look far better than in RGB.

    Args:
        colours (Sequence[Sequence[float]]): RGB colours, 0-255.

    Returns:
        np.ndarray: One L, a, b row per colour.
    """
    return cv2.cvtColor(np.array(colours, dtype=np.float32).reshape(1, -1, 3) / 255, cv2.COLOR_RGB2LAB)[0]


def assignColours(stickers: Sequence[Sequence[float]]) -> str:
    """Names all 54 stickers at once against the cube's own centres, nine to each colour.

    The centres are seen under the same light as everything else, so they make better references than
    fixed values. A glared centre spoils its colour though, so that has to be caught when scanning.

    Args:
        stickers (Sequence[Sequence[float]]): Every sticker's measured RGB colour, in Cube.state
            order, so each face's centre is the colour that face is in the solved cube.

    Returns:
        str: The cube state.
    """
    lab = toLab(stickers)
    others = [i for i in range(54) if i not in CENTRES]
    names = [SOLVED_MASK[i] for i in CENTRES]
    distances = np.linalg.norm(lab[:, None, :] - lab[CENTRES][None, :, :], axis=2)

    # closest pairs first, until each colour has its nine
    state = [SOLVED_MASK[i] if i in CENTRES else "" for i in range(54)]
    room = [8] * 6
    for i, colour in sorted(((i, c) for i in others for c in range(6)), key=lambda p: distances[p]):
        if not state[i] and room[colour]:
            state[i] = names[colour]
            room[colour] -= 1

    # greedy can push a displaced sticker down a chain (white to orange to yellow), so swap any two
    # while it lowers the total. on the synthetic cubes this matched scipy's exact assignment
    index = {name: colour for colour, name in enumerate(names)}
    improved = True
    while improved:
        improved = False
        for a in others:
            for b in others:
                ca, cb = index[state[a]], index[state[b]]
                if ca != cb and distances[a, cb] + distances[b, ca] < distances[a, ca] + distances[b, cb] - 1e-9:
                    state[a], state[b] = state[b], state[a]
                    improved = True
    return "".join(state)


# the four sides are a quarter turn apart, then white and yellow need a tilt
SCAN_ORDER = "RBOGWY"
# the face that goes on top when each one is shown, so it's read the way Cube.state lays it out
SCAN_TOPS = {"R": "W", "B": "W", "O": "W", "G": "W", "W": "O", "Y": "R"}

# timings in seconds, distances in LAB. the distances will want checking on a real camera: the
# closest two different centres got on the synthetic frames was ~21 apart (white and yellow,
# overexposed), and noise moved a sticker by up to ~15 between frames of the same face
SETTLE_TIME = 0.3
COLLECT_TIME = 0.5
LOST_TIME = 0.3
STEADY_DISTANCE = 25
NEW_FACE_DISTANCE = 15


class GuidedScan:
    """Asks for the faces one at a time in SCAN_ORDER and turns camera readings into a cube state.

    There's no camera or Tk in here so it can be tested, CubeScanner feeds it a reading per frame.
    Once a face appears it's left to settle, then the median of a short run of steady readings is
    taken. After a capture nothing is read until a face with a different centre shows up.
    """

    def __init__(self) -> None:
        self.faces: dict[str, list[tuple[float, float, float]]] = {}
        self.state: str | None = None
        self.problems: list[str] = []
        self.message = ""
        self.waitFor = None
        self.restart()

    def restart(self, now: float | None = None) -> None:
        """Forgets the face in view, so it has to settle from scratch.

        Args:
            now (float, optional): When a face is still in view, the time to settle it from.
        """
        self.seen = now
        self.lastSeen = now
        self.readings = []
        self.collectStart = 0.0
        self.progress = 0.0

    @property
    def done(self) -> bool:
        return len(self.faces) == 6

    def prompt(self) -> tuple[str, str] | None:
        """The face to show next and the face that goes on top of it, or None once all six are in."""
        if self.done:
            return None
        face = SCAN_ORDER[len(self.faces)]
        return face, SCAN_TOPS[face]

    def addReading(self, colours: list[tuple[float, float, float]] | None, now: float) -> None:
        """Takes one frame's readFaceColours result.

        Args:
            colours (list[tuple[float, float, float]] | None): The nine measured colours, or None if no
                face was found in the frame.
            now (float): The time of the frame, in seconds.
        """
        if self.done:
            return

        if colours is None:
            # one missed frame is fine, a face gone for longer has to settle again
            if self.lastSeen is not None and now - self.lastSeen > LOST_TIME:
                self.restart()
            return
        self.lastSeen = now

        centre = toLab([colours[4]])[0]
        if self.waitFor is not None:
            if np.linalg.norm(centre - self.waitFor) < NEW_FACE_DISTANCE:
                return
            self.waitFor = None

        if self.seen is None:
            self.seen = now
        if now - self.seen < SETTLE_TIME:
            return

        # the cube moved, let it settle again
        if self.readings and np.linalg.norm(toLab(colours) - toLab(self.readings[0]), axis=1).max() > STEADY_DISTANCE:
            self.restart(now)
            return
        if not self.readings:
            self.collectStart = now
        self.readings.append(colours)
        self.progress = min(1.0, (now - self.collectStart) / COLLECT_TIME)

        if now - self.collectStart >= COLLECT_TIME:
            self.capture([(float(r), float(g), float(b)) for r, g, b in np.median(self.readings, axis=0)])

    def capture(self, colours: list[tuple[float, float, float]]) -> None:
        face = SCAN_ORDER[len(self.faces)]
        centre = toLab([colours[4]])[0]
        self.restart()

        for other, otherColours in self.faces.items():
            if np.linalg.norm(centre - toLab([otherColours[4]])[0]) < NEW_FACE_DISTANCE:
                self.message = f"that looks like the {PLOTTING_COLOUR_MAP[other].lower()} face again"
                self.waitFor = centre
                return

        # glare that covers most of the centre reads as clipped white. white's centre is meant to be
        # white, and glare on it doesn't matter anyway
        if face != "W" and min(colours[4]) >= 245:
            self.message = "glare on the centre, tilt the cube a little"
            return

        self.faces[face] = colours
        self.waitFor = centre
        if self.done:
            self.finish()
        else:
            self.message = "got it"

    def finish(self) -> None:
        """Names all 54 stickers once every face is in and checks the result is a real cube."""
        stickers = [c for face in SOLVED_MASK[4::9] for c in self.faces[face]]
        self.state = assignColours(stickers)
        self.problems = validateCube(self.state)
        self.message = "that isn't a real cube, go back and rescan" if self.problems else "looks good, press End Scan"

    def back(self) -> None:
        """Drops the last face so it can be scanned again."""
        if self.faces:
            self.faces.popitem()
        self.state = None
        self.problems = []
        self.message = ""
        self.waitFor = None
        self.restart()

    def missing(self) -> list[str]:
        """The faces still to scan, by colour name."""
        return [PLOTTING_COLOUR_MAP[face].lower() for face in SCAN_ORDER if face not in self.faces]
