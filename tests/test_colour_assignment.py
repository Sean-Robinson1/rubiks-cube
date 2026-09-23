import random
import unittest
from dataclasses import replace

from scanner_images import CASES, STANDARD_RGB, STICKER_RGB, Case, renderCube

from rubiks_cube.constants import SOLVED_MASK
from rubiks_cube.cube import Cube
from rubiks_cube.cube_validation import validateCube
from rubiks_cube.scanner_utils import assignColours, readFaceColours

_byName = {c.name: c for c in CASES}

# lighting and camera conditions for a whole cube. the detection failures (large, tilt30, stickerless)
# are left out, they never get as far as colours
CONDITIONS: dict[str, tuple[Case, list[float] | None]] = {
    name: (_byName[name], None)
    for name in [
        "baseline",
        "small",
        "offCentre",
        "tilt10",
        "perspective",
        "dim",
        "bright",
        "warmLight",
        "glare",
        "noise",
        "blur",
        "clutter",
        "otherCamera",
    ]
}
CONDITIONS["exposureVaries"] = (_byName["baseline"], [0.7, 1.15, 0.85, 1.25, 0.75, 1.05])
CONDITIONS["glareOnCentre"] = (replace(_byName["glare"], glareAt=(0.0, 0.0)), None)

# in the SCAN_COLOURS camera's palette glare turns orange into their yellow and yellow into white, so
# the pixels can't tell them apart and the nine-of-each rule only sometimes recovers it. validateCube
# catches every one of these
KNOWN = {
    ("glare", "camera"): "glare makes orange read as yellow and yellow as white in this palette",
    ("glareOnCentre", "camera"): "glare on every centre spoils the references, needs catching at scan time",
}

PALETTES = {"camera": STICKER_RGB, "standard": STANDARD_RGB}


def _scrambles(n: int = 3) -> list[str]:
    random.seed(0)
    cube = Cube()
    out = []
    for _ in range(n):
        cube.randomise()
        out.append(cube.state)
    return out


SCRAMBLES = _scrambles()
_measured: dict[tuple[str, str, str], list[tuple[float, float, float]] | None] = {}


def measure(condition: str, palette: str, state: str) -> list[tuple[float, float, float]] | None:
    """Every sticker's measured colour for one cube, rendering it only once per test run."""
    key = (condition, palette, state)
    if key not in _measured:
        case, exposure = CONDITIONS[condition]
        if case.palette is STICKER_RGB:
            case = replace(case, palette=PALETTES[palette])
        stickers: list[tuple[float, float, float]] | None = []
        for frame in renderCube(state, case, exposure):
            face = readFaceColours(frame)
            if face is None:
                stickers = None
                break
            stickers = stickers + face
        _measured[key] = stickers
    return _measured[key]


class TestAssignColours(unittest.TestCase):
    def test_exactColours(self):
        rgb = {name[0]: colour for name, colour in STICKER_RGB.items()}
        for state in [SOLVED_MASK] + SCRAMBLES:
            self.assertEqual(assignColours([rgb[c] for c in state]), state)

    def test_inBetweenStickerSettledByCounts(self):
        # one red sticker read halfway to orange: the orange side already has its nine, so it's red
        rgb = {name[0]: colour for name, colour in STANDARD_RGB.items()}
        state = SCRAMBLES[0]
        stickers: list[tuple[float, ...]] = [tuple(map(float, rgb[c])) for c in state]
        i = next(i for i, c in enumerate(state) if c == "R" and i % 9 != 4)
        red, orange = rgb["R"], rgb["O"]
        stickers[i] = tuple(r * 0.45 + o * 0.55 for r, o in zip(red, orange))
        self.assertEqual(assignColours(stickers), state)

    def test_neverSilentlyWrong(self):
        # whatever the conditions, a scan comes back as the right cube or one validateCube rejects
        for condition in CONDITIONS:
            for palette in PALETTES:
                for state in SCRAMBLES:
                    stickers = measure(condition, palette, state)
                    if stickers is None:
                        self.fail(f"{condition} {palette}: a face wasn't found")
                    got = assignColours(stickers)
                    if got != state:
                        self.assertTrue(validateCube(got), f"{condition} {palette}: wrong and not caught")


class TestWholeCube(unittest.TestCase):
    # one test per condition and palette, added below. KNOWN ones are expected failures, so fixing one
    # shows up as an unexpected success
    pass


def _makeTest(condition: str, palette: str):
    def test(self: unittest.TestCase):
        for state in SCRAMBLES:
            stickers = measure(condition, palette, state)
            if stickers is None:
                self.fail(f"{condition} {palette}: a face wasn't found")
            self.assertEqual(assignColours(stickers), state)

    return unittest.expectedFailure(test) if (condition, palette) in KNOWN else test


for _condition in CONDITIONS:
    for _palette in PALETTES:
        setattr(TestWholeCube, f"test_{_condition}_{_palette}", _makeTest(_condition, _palette))


if __name__ == "__main__":
    unittest.main()
