import unittest

import cv2

from rubiks_cube.constants import SCAN_COLOURS
from rubiks_cube.scanner_utils import readFace

from scanner_images import CASES, render


class TestReadFace(unittest.TestCase):
    # one test per case in scanner_images.CASES, added below. run `python tests/scanner_images.py` to
    # see the frames. cases with a knownIssue are expected failures, so fixing one shows up as an
    # unexpected success - drop its knownIssue then
    pass


def _makeTest(case):
    def test(self):
        # kmeans starts from random centres, fix them so a reading can't change between runs
        cv2.setRNGSeed(0)
        self.assertEqual(readFace(render(case), SCAN_COLOURS), case.stickers, case.description)

    test.__doc__ = case.description
    return unittest.expectedFailure(test) if case.knownIssue else test


for _case in CASES:
    setattr(TestReadFace, f"test_{_case.name}", _makeTest(_case))


if __name__ == "__main__":
    unittest.main()
