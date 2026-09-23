import logging
from tkinter import Label

import cv2
import numpy as np
from PIL import Image, ImageTk

from .constants import SCAN_COLOURS
from .scanner_utils import displayFace, readFace


class CubeScanner:
    def __init__(self, videoLabel: Label, calibratedColours: dict[str, np.ndarray] | None = None) -> None:
        """Initialises the CubeScanner with a video label and optional calibrated colours.

        Args:
            videoLabel (Label): The Tkinter label to display the video feed.
            calibratedColours (dict[str, np.ndarray], optional): A dictionary of calibrated colours. Defaults to None.
        """
        logging.info("Initialising CubeScanner")
        self.videoLabel = videoLabel
        self.vid = cv2.VideoCapture(0)
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

        self.previous = []
        self.previousCount = 0

        if calibratedColours is not None:
            self.colours = []
            for colourName, rgb in calibratedColours.items():
                self.colours.append((colourName, rgb))
        else:
            self.colours = SCAN_COLOURS

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

        output = frame.copy()
        colours = readFace(frame, self.colours, output)
        if colours is not None:
            # compares to previous scan
            if self.previous == colours:
                self.previousCount += 1
                if self.previousCount >= 3:
                    self.previousFaces[colours[4]] = colours
            else:
                self.previous = colours
                self.previousCount = 0

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
            logging.warning(f"Error updating image: {e}")

        # Schedule next frame only if still running and label exists
        if self.running and self.videoLabel.winfo_exists():
            self.videoLabel.after(10, self.updateFrame)

    def stop(self) -> None:
        """Stops the webcam recording and releases the video."""
        self.running = False
        if hasattr(self, "vid") and self.vid.isOpened():
            self.vid.release()

    def getCubeString(self) -> str | None:
        """Returns the cube string representation of the scanned cube.

        Returns:
            str | None: The cube string representation, or None if not all faces are scanned.
        """
        cubeString = ""
        for face in ["White", "Green", "Red", "Blue", "Orange", "Yellow"]:
            if self.previousFaces[face] == []:
                return None
            for colour in self.previousFaces[face]:
                cubeString += colour[0]

        for colour in ["W", "G", "R", "B", "O", "Y"]:
            if cubeString.count(colour) != 9:
                return None

        logging.debug(f"Scanned cube: {cubeString}")

        return cubeString
