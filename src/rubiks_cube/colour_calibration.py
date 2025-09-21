import tkinter as tk

import cv2
import numpy as np
from PIL import Image, ImageTk

from .constants import FACE_KEYS
from .scanner_utils import bgr2rgb, getDominantColours


class CubeCalibrator:
    def __init__(self, videoLabel: tk.Label) -> None:
        """Initialises the CubeCalibrator with a video label.

        Args:
            videoLabel (tk.Label): The Tkinter label to display the video feed.
        """
        self.videoLabel = videoLabel

        # default display colours (BGR tuples for cv2 drawing)
        self.defaultColours: dict[str, np.ndarray] = {
            "Red": np.array([0, 0, 255]),
            "Green": np.array([0, 255, 0]),
            "Blue": np.array([255, 0, 0]),
            "Yellow": np.array([0, 255, 255]),
            "Orange": np.array([0, 165, 255]),
            "White": np.array([255, 255, 255]),
        }

        self.avgColours = {n: [np.zeros(3, dtype=float), 0] for n in self.defaultColours}

        self.currentFace = None
        self.running = True
        self.photo = None
        self.vid = cv2.VideoCapture(0)
        self.squareSize = 200

        self.videoLabel.bind("<Key>", self.keyPressed)
        self.videoLabel.focus_set()

        self.updateFrame()

    def keyPressed(self, event: tk.Event) -> None:
        """Handle key press events to set the current face or quit.

        Args:
            event (tk.Event): The key press event.
        """
        key = getattr(event, "char", "").lower()
        if key in FACE_KEYS:
            self.currentFace = FACE_KEYS[key]

    def extractCells(self, img: np.ndarray) -> list[np.ndarray]:
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

    def displayColours(self, frame: np.ndarray, colours: dict[str, tuple[np.ndarray, int]]) -> np.ndarray:
        """Display the current averaged colours on the frame.

        Args:
            frame (np.ndarray): The frame to draw on.
            colours (dict[str, tuple[np.ndarray, int]]): The current averaged colours and their counts.

        Returns:
            np.ndarray: The frame with the colours drawn on it.
        """
        startx, starty = 10, 10
        width, jump = 36, 44
        counter = 0
        for name, (sumcol, count) in colours.items():
            if count > 0:
                avg = (sumcol / count).astype(np.uint8)
                bgr = [int(avg[2]), int(avg[1]), int(avg[0])]
            else:
                bgr = [int(c) for c in self.defaultColours[name]]
            cv2.rectangle(
                frame, (startx + jump * counter, starty), (startx + width + jump * counter, starty + width), bgr, -1
            )
            cv2.putText(
                frame,
                name[0],
                (startx + jump * counter + 6, starty + width + 16),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (200, 200, 200),
                1,
            )
            counter += 1
        if self.currentFace:
            cv2.putText(
                frame,
                f"Recording: {self.currentFace}",
                (10, frame.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.6,
                (0, 255, 0),
                2,
            )
        return frame

    def updateFrame(self) -> None:
        """Update the video frame from the webcam and process it. Records the colours of the current face if set.
        Displays the current averaged colours and the cropped square."""
        if not self.running:
            if self.vid.isOpened():
                self.vid.release()
            return

        ret, frame = self.vid.read()
        if not ret:
            self.videoLabel.after(50, self.updateFrame)
            return

        h, w = frame.shape[:2]
        cx, cy = w // 2, h // 2

        minx, miny = max(cx - self.squareSize // 2, 0), max(cy - self.squareSize // 2, 0)
        maxx, maxy = min(cx + self.squareSize // 2, w), min(cy + self.squareSize // 2, h)

        cropped = frame[miny:maxy, minx:maxx].copy()

        cv2.rectangle(frame, (minx, miny), (maxx, maxy), (0, 255, 0), 2)

        cells = self.extractCells(cropped)
        dominantColours = []
        for cell in cells:
            dom = getDominantColours(cell, 1)[0]
            dominantColours.append(dom)

        if self.currentFace:
            for col in dominantColours:
                self.avgColours[self.currentFace][0] += np.array(col)
                self.avgColours[self.currentFace][1] += 1

            self.currentFace = None

        display = frame.copy()
        display = self.displayColours(display, self.avgColours)

        inset_h = 200
        inset_w = int(cropped.shape[1] * inset_h / max(1, cropped.shape[0]))
        inset = cv2.resize(cropped, (inset_w, inset_h))
        display[10 : 10 + inset_h, display.shape[1] - inset_w - 10 : display.shape[1] - 10] = inset

        w = round(self.videoLabel.winfo_width() * 0.9)
        h = round(self.videoLabel.winfo_height() * 0.9)
        if w <= 1 or h <= 1:
            h, w = display.shape[:2]

        frame_resized = cv2.resize(display, (w, h), interpolation=cv2.INTER_LINEAR)

        rgb = cv2.cvtColor(frame_resized, cv2.COLOR_BGR2RGB)
        pil_img = Image.fromarray(rgb)
        tk_img = ImageTk.PhotoImage(pil_img, master=self.videoLabel)
        self.photo = tk_img
        self.videoLabel.config(image=self.photo)

        if self.running and self.videoLabel.winfo_exists():
            self.videoLabel.after(30, self.updateFrame)

    def stop(self) -> None:
        """Stops the webcam recording and releases the video."""
        self.running = False
        if hasattr(self, "vid") and self.vid.isOpened():
            self.vid.release()

    def getAverages(self) -> dict[str, np.ndarray]:
        """Return averaged RGB colours."""
        out = {}
        for k, (sumcol, count) in self.avgColours.items():
            out[k] = (sumcol / count) if count > 0 else bgr2rgb(self.defaultColours[k])

        return out
