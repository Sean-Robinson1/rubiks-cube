import unittest
from dataclasses import replace

import cv2
from scanner_images import BY_NAME, STANDARD_RGB, renderCube
from test_cube_validation import scrambled

from rubiks_cube.constants import SOLVED_MASK
from rubiks_cube.cross_table import EDGES
from rubiks_cube.scanner_utils import SCAN_ORDER, SCAN_TOPS, GuidedScan, readFaceColours

FRAME = 1 / 30


def readings(state: str, case=BY_NAME["baseline"]) -> dict:
    """Each face's readFaceColours result, by face letter."""
    frames = renderCube(state, case)
    return {face: readFaceColours(frames[SOLVED_MASK[4::9].index(face)]) for face in SOLVED_MASK[4::9]}


class Feeder:
    """Feeds a GuidedScan one reading per frame with a simulated clock."""

    def __init__(self) -> None:
        self.scan = GuidedScan()
        self.now = 0.0

    def show(self, reading, seconds: float) -> None:
        for _ in range(round(seconds / FRAME)):
            self.scan.addReading(reading, self.now)
            self.now += FRAME


def scanAll(faces: dict) -> GuidedScan:
    feeder = Feeder()
    for face in SCAN_ORDER:
        feeder.show(faces[face], 1.0)
    return feeder.scan


class TestGuidedScan(unittest.TestCase):
    def test_scanTopsMatchTheLayout(self):
        # the face along each face's top row in Cube.state, which is what has to be shown on top
        partner = {a: b for a, b in EDGES} | {b: a for a, b in EDGES}
        for face, top in SCAN_TOPS.items():
            self.assertEqual(SOLVED_MASK[partner[SOLVED_MASK.index(face) + 1]], top, face)

    def test_fullScan(self):
        state = scrambled()
        for case in (BY_NAME["baseline"], BY_NAME["dim"], BY_NAME["warmLight"], BY_NAME["noise"]):
            for palette in (case.palette, STANDARD_RGB):
                scan = scanAll(readings(state, replace(case, palette=palette)))
                self.assertEqual(scan.state, state, case.name)
                self.assertEqual(scan.problems, [])
                self.assertIn("looks good", scan.message)

    def test_settleThenCollect(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 0.25)
        self.assertEqual(feeder.scan.progress, 0)
        feeder.show(faces["R"], 0.45)
        self.assertEqual(feeder.scan.faces, {})
        feeder.show(faces["R"], 0.2)
        self.assertEqual(list(feeder.scan.faces), ["R"])

    def test_movingRestartsTheSettle(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 0.6)
        # a different reading mid-collection, as if the cube moved, then steady again
        feeder.show(faces["B"], 0.7)
        self.assertEqual(feeder.scan.faces, {})
        feeder.show(faces["B"], 0.2)
        self.assertIn("R", feeder.scan.faces)

    def test_oneMissedFrameIsFine(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 0.5)
        feeder.show(None, FRAME)
        feeder.show(faces["R"], 0.35)
        self.assertEqual(list(feeder.scan.faces), ["R"])

    def test_faceGoneTooLongSettlesAgain(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 0.5)
        feeder.show(None, 0.5)
        feeder.show(faces["R"], 0.5)
        self.assertEqual(feeder.scan.faces, {})
        feeder.show(faces["R"], 0.4)
        self.assertEqual(list(feeder.scan.faces), ["R"])

    def test_sameFaceIsIgnoredAfterCapture(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 3.0)
        self.assertEqual(list(feeder.scan.faces), ["R"])
        self.assertEqual(feeder.scan.message, "got it")

    def test_repeatFace(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 1.0)
        feeder.show(faces["B"], 1.0)
        feeder.show(faces["R"], 1.0)
        self.assertEqual(list(feeder.scan.faces), ["R", "B"])
        self.assertIn("red face again", feeder.scan.message)

    def test_glareOnTheCentre(self):
        state = scrambled()
        frame = renderCube(state, BY_NAME["baseline"])[SOLVED_MASK[4::9].index("R")]
        # clipped white over most of the centre sticker, the way real glare saturates
        cv2.circle(frame, (320, 240), 17, (255, 255, 255), -1)
        glared = readFaceColours(frame)
        self.assertIsNotNone(glared)
        feeder = Feeder()
        feeder.show(glared, 1.0)
        self.assertEqual(feeder.scan.faces, {})
        self.assertIn("glare", feeder.scan.message)

    def test_back(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 1.0)
        feeder.show(faces["B"], 1.0)
        feeder.scan.back()
        self.assertEqual(list(feeder.scan.faces), ["R"])
        self.assertEqual(feeder.scan.prompt(), ("B", "W"))
        feeder.show(faces["B"], 1.0)
        self.assertEqual(list(feeder.scan.faces), ["R", "B"])

    def test_missing(self):
        faces = readings(scrambled())
        feeder = Feeder()
        feeder.show(faces["R"], 1.0)
        self.assertEqual(feeder.scan.missing(), ["blue", "orange", "green", "white", "yellow"])

    def test_faceShownRotated(self):
        # the green face held a quarter turn out: a real cube can't look like that
        faces = readings(scrambled())
        green = faces["G"]
        faces["G"] = [green[i] for i in (6, 3, 0, 7, 4, 1, 8, 5, 2)]
        scan = scanAll(faces)
        self.assertTrue(scan.done)
        self.assertTrue(scan.problems)
        self.assertIn("isn't a real cube", scan.message)


if __name__ == "__main__":
    unittest.main()
