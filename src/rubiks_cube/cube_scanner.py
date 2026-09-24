import logging
import time
from tkinter import Label

import cv2
import numpy as np
from PIL import Image, ImageTk

from .constants import PLOTTING_COLOUR_MAP, SOLVED_MASK, USUAL_COLOUR_VALUES
from .scanner_utils import GuidedScan, displayFace, readFaceColours


class CubeScanner:
    def __init__(self, videoLabel: Label) -> None:
        """Initialises the CubeScanner with a video label.

        Args:
            videoLabel (Label): The Tkinter label to display the video feed.
        """
        logging.info("Initialising CubeScanner")
        self.videoLabel = videoLabel
        self.vid = cv2.VideoCapture(0)
        self.scan = GuidedScan()
        self.running = True
        self.photo = None

        self.updateFrame()

    def updateFrame(self) -> None:
        """Gets a frame from the VideoCapture, reads any cube face in it into the scan and shows the
        frame with the scan's prompt drawn on."""
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
        self.scan.addReading(readFaceColours(frame, output), time.monotonic())
        self.drawScan(output)

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

    def drawScan(self, output: np.ndarray) -> None:
        """Draws the prompt, the capture progress, any message and the map of faces scanned so far.

        Args:
            output (np.ndarray): The frame to draw on.
        """
        h = output.shape[0]

        def text(line: str, y: int, scale: float = 0.7) -> None:
            # dark outline under white so it reads on any background
            cv2.putText(output, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (0, 0, 0), 4, cv2.LINE_AA)
            cv2.putText(output, line, (20, y), cv2.FONT_HERSHEY_SIMPLEX, scale, (255, 255, 255), 2, cv2.LINE_AA)

        prompt = self.scan.prompt()
        if prompt is not None:
            face, top = prompt
            name, topName = PLOTTING_COLOUR_MAP[face], PLOTTING_COLOUR_MAP[top]
            text(f"{len(self.scan.faces) + 1}/6: show the {name.lower()} face, {topName.lower()} on top", h - 50)

            # the face to show, with a bar along its top in the colour that goes on top
            cv2.rectangle(output, (20, h - 130), (70, h - 80), USUAL_COLOUR_VALUES[name], -1)
            cv2.rectangle(output, (20, h - 142), (70, h - 134), USUAL_COLOUR_VALUES[topName], -1)
            if self.scan.progress:
                cv2.rectangle(output, (90, h - 110), (90 + int(200 * self.scan.progress), h - 100), (0, 255, 0), -1)

        text(self.scan.message, h - 20)
        # the first few only, the view is needed for rescanning. End Scan lists them all
        problems = self.scan.problems[:3]
        if len(self.scan.problems) > 3:
            problems.append(f"and {len(self.scan.problems) - 3} more")
        for i, problem in enumerate(reversed(problems)):
            text(problem, h - 50 - 22 * i, 0.5)

        # measured colours while scanning, the names they were given once all six are in
        for face, colours in self.scan.faces.items():
            if self.scan.state is not None:
                start = SOLVED_MASK[4::9].index(face) * 9
                shown = [USUAL_COLOUR_VALUES[PLOTTING_COLOUR_MAP[c]] for c in self.scan.state[start : start + 9]]
            else:
                shown = [(b, g, r) for r, g, b in colours]
            displayFace(output, face, shown)

    def stop(self) -> None:
        """Stops the webcam recording and releases the video."""
        self.running = False
        if hasattr(self, "vid") and self.vid.isOpened():
            self.vid.release()

    def back(self) -> None:
        """Drops the last scanned face so it can be scanned again."""
        self.scan.back()

    def getCubeString(self) -> tuple[str | None, list[str]]:
        """Returns the scanned cube, or what's stopping it being used.

        Returns:
            tuple[str | None, list[str]]: The cube state and the problems with it. The state is only
            safe to use when there are no problems.
        """
        if not self.scan.done:
            return None, ["still to scan: " + ", ".join(self.scan.missing())]

        logging.debug(f"Scanned cube: {self.scan.state}")

        return self.scan.state, self.scan.problems
