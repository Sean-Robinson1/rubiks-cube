import os
import unittest

import cv2
from scanner_images import CASES, DEFAULT_DIR, render, summaryText

from rubiks_cube.constants import SCAN_COLOURS
from rubiks_cube.scanner_utils import readFace

# every reading, so tearDownModule can write the summary once they're all in
_readings = {}


class TestReadFace(unittest.TestCase):
    # one test per case in scanner_images.CASES, added below. run `python tests/scanner_images.py` to
    # see the frames. cases with a knownIssue are expected failures, so fixing one shows up as an
    # unexpected success - drop its knownIssue then
    pass


def _makeTest(case):
    def test(self):
        # kmeans starts from random centres, fix them so a reading can't change between runs
        cv2.setRNGSeed(0)
        read = readFace(render(case), SCAN_COLOURS)
        _readings[case.name] = read
        self.assertEqual(read, case.stickers, case.description)

    test.__doc__ = case.description
    return unittest.expectedFailure(test) if case.knownIssue else test


for _case in CASES:
    setattr(TestReadFace, f"test_{_case.name}", _makeTest(_case))


def tearDownModule():
    # refresh scanner_images/summary.txt, but only after a full run - a `-k` subset would overwrite it
    # with a partial one
    if len(_readings) != len(CASES):
        return
    os.makedirs(DEFAULT_DIR, exist_ok=True)
    with open(os.path.join(DEFAULT_DIR, "summary.txt"), "w", encoding="utf-8") as handle:
        handle.write(summaryText([(case, _readings[case.name]) for case in CASES]))


if __name__ == "__main__":
    unittest.main()
