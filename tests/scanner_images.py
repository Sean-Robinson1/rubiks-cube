"""Synthetic webcam frames of a cube face, for testing readFace without a camera.

Run it to write every case out as a png plus a contact sheet with what readFace made of each:

    python tests/scanner_images.py [outdir]

pngs are gitignored, so the tests build the frames in memory instead of loading files.
"""

import os
import sys
from dataclasses import dataclass, field

import cv2
import numpy as np

from rubiks_cube.constants import SCAN_COLOURS

FRAME_W, FRAME_H = 640, 480

# stickers as the camera behind SCAN_COLOURS saw them, so the baseline tests the pipeline rather
# than the reference values. RGB
STICKER_RGB = {name: tuple(int(round(v)) for v in rgb) for name, rgb in SCAN_COLOURS}

# a more saturated camera. its yellow sits nearer SCAN_COLOURS orange than SCAN_COLOURS yellow
OTHER_CAMERA_RGB = {
    "White": (235, 235, 230),
    "Yellow": (240, 215, 35),
    "Red": (195, 30, 40),
    "Orange": (245, 115, 25),
    "Blue": (25, 75, 195),
    "Green": (25, 160, 75),
}

# row-major, same order readFace returns
MIXED = ["Red", "White", "Blue", "Yellow", "Green", "Orange", "White", "Red", "Blue"]
RED_ORANGE = ["Red", "Orange", "Red", "Orange", "Red", "Orange", "Red", "Orange", "Red"]
WHITE_YELLOW = ["White", "Yellow", "White", "Yellow", "White", "Yellow", "White", "Yellow", "White"]
SOLVED_WHITE = ["White"] * 9


@dataclass
class Case:
    name: str
    description: str
    stickers: list[str] = field(default_factory=lambda: list(MIXED))
    faceSize: int = 150  # px across the whole face
    centre: tuple[int, int] = (FRAME_W // 2, FRAME_H // 2)
    rotation: float = 0.0  # degrees, in the image plane
    skew: float = 0.0  # perspective: how much narrower the far edge is, 0-1
    brightness: float = 1.0
    tint: tuple[float, float, float] = (1.0, 1.0, 1.0)  # per channel RGB gain, a colour cast
    glare: float = 0.0  # peak brightness added by a specular spot, 0-255
    noise: float = 0.0  # gaussian sensor noise sigma
    blur: int = 0  # gaussian blur kernel, odd, 0 for none
    clutter: bool = False  # busy coloured background
    stickerless: bool = False  # no black plastic between the stickers
    palette: dict = field(default_factory=lambda: STICKER_RGB)
    knownIssue: str = ""  # why readFace currently gets this wrong, empty if it shouldn't


CASES = [
    Case("baseline", "centred, square on, even light"),
    Case("solvedFace", "all nine stickers the same colour", stickers=list(SOLVED_WHITE)),
    Case("small", "held far from the camera", faceSize=105),
    Case(
        "large",
        "held close to the camera",
        faceSize=260,
        knownIssue="sticker area limits are absolute pixels (300-2000), a close face is over",
    ),
    Case("offCentre", "near the top left of the frame", centre=(160, 130)),
    Case("tilt10", "rotated 10 degrees", rotation=10, knownIssue="face crop is an axis aligned box, and cells straddling two colours read differently per kmeans seed"),
    Case("tilt30", "rotated 30 degrees", rotation=30, knownIssue="face crop is an axis aligned box"),
    Case("perspective", "viewed from slightly below", skew=0.15, knownIssue="face crop is an axis aligned box, and cells straddling two colours read differently per kmeans seed"),
    Case("dim", "dark room", brightness=0.45, knownIssue="fixed RGB references, nothing normalises brightness"),
    Case("bright", "overexposed", brightness=1.35, knownIssue="fixed RGB references, washed out yellow is nearer white"),
    Case(
        "warmLight",
        "tungsten bulb colour cast",
        tint=(1.15, 1.0, 0.7),
        knownIssue="fixed RGB references, nothing corrects white balance",
    ),
    Case(
        "glare",
        "specular highlight across the stickers",
        glare=170,
        knownIssue="getDominantColours takes kmeans cluster 0, not the biggest. passes with the biggest",
    ),
    Case("noise", "grainy low light sensor", noise=14),
    Case("blur", "slightly out of focus", blur=7),
    Case("clutter", "busy coloured background", clutter=True),
    Case("redOrange", "alternating red and orange", stickers=list(RED_ORANGE)),
    Case("redOrangeWarm", "red and orange under warm light", stickers=list(RED_ORANGE), tint=(1.15, 1.0, 0.7)),
    Case("whiteYellow", "alternating white and yellow", stickers=list(WHITE_YELLOW)),
    Case(
        "otherCamera",
        "a camera with more saturated colours than the one SCAN_COLOURS came from",
        palette=OTHER_CAMERA_RGB,
        knownIssue="fixed SCAN_COLOURS references, this camera's yellow is nearer their orange",
    ),
    Case(
        "stickerless",
        "stickerless cube, no black between the tiles",
        stickerless=True,
        knownIssue="detection relies on the dark gaps between stickers to find them",
    ),
]


def renderFlatFace(case: Case) -> np.ndarray:
    """The face as a square BGR image, before any camera effects."""
    size = case.faceSize
    body = (60, 60, 60) if case.stickerless else (20, 20, 20)
    face = np.full((size, size, 3), body, dtype=np.uint8)
    cell = size / 3
    gap = 0.0 if case.stickerless else cell * 0.08
    for i, name in enumerate(case.stickers):
        row, col = divmod(i, 3)
        r, g, b = case.palette[name]
        x0, y0 = int(col * cell + gap), int(row * cell + gap)
        x1, y1 = int((col + 1) * cell - gap), int((row + 1) * cell - gap)
        cv2.rectangle(face, (x0, y0), (x1 - 1, y1 - 1), (b, g, r), -1)
    return face


def background(case: Case, rng: np.random.Generator) -> np.ndarray:
    frame = np.full((FRAME_H, FRAME_W, 3), (95, 100, 105), dtype=np.uint8)
    # a soft gradient so it isn't perfectly flat
    frame = (frame * np.linspace(0.85, 1.1, FRAME_W)[None, :, None]).clip(0, 255).astype(np.uint8)
    if case.clutter:
        for _ in range(25):
            x, y = int(rng.integers(0, FRAME_W)), int(rng.integers(0, FRAME_H))
            w, h = int(rng.integers(20, 120)), int(rng.integers(20, 120))
            colour = tuple(int(c) for c in rng.integers(0, 256, 3))
            cv2.rectangle(frame, (x, y), (x + w, y + h), colour, -1)
    return frame


def render(case: Case, seed: int = 0) -> np.ndarray:
    """Renders one case as a BGR webcam frame."""
    rng = np.random.default_rng(seed)
    face = renderFlatFace(case)
    size = case.faceSize
    frame = background(case, rng)

    # where the face's four corners land: skew narrows the top edge, then rotate about the centre
    half = size / 2
    inset = half * case.skew
    corners = np.array([[-half + inset, -half], [half - inset, -half], [half, half], [-half, half]])
    theta = np.deg2rad(case.rotation)
    rot = np.array([[np.cos(theta), -np.sin(theta)], [np.sin(theta), np.cos(theta)]])
    dst = (corners @ rot.T + case.centre).astype(np.float32)
    src = np.array([[0, 0], [size, 0], [size, size], [0, size]], dtype=np.float32)
    matrix = cv2.getPerspectiveTransform(src, dst)

    warped = cv2.warpPerspective(face, matrix, (FRAME_W, FRAME_H))
    mask = cv2.warpPerspective(np.full((size, size), 255, np.uint8), matrix, (FRAME_W, FRAME_H))
    frame[mask > 0] = warped[mask > 0]

    img = frame.astype(np.float32)
    # tint is RGB, the frame is BGR
    img *= case.brightness * np.array(case.tint[::-1], dtype=np.float32)
    if case.glare:
        ys, xs = np.mgrid[0:FRAME_H, 0:FRAME_W]
        gx, gy = case.centre[0] - size * 0.15, case.centre[1] - size * 0.2
        spot = np.exp(-(((xs - gx) ** 2) / (2 * (size * 0.18) ** 2) + ((ys - gy) ** 2) / (2 * (size * 0.1) ** 2)))
        img += (case.glare * spot)[:, :, None]
    if case.noise:
        img += rng.normal(0, case.noise, img.shape)
    img = img.clip(0, 255).astype(np.uint8)
    if case.blur:
        img = cv2.GaussianBlur(img, (case.blur, case.blur), 0)
    return img


def contactSheet(results: list[tuple[Case, np.ndarray, list[str] | None]]) -> np.ndarray:
    """Tiles every case with its name, what readFace read, and whether that was right."""
    tileW, tileH, cols = 320, 280, 4
    rows = -(-len(results) // cols)
    sheet = np.full((rows * tileH, cols * tileW, 3), 255, dtype=np.uint8)
    for i, (case, frame, read) in enumerate(results):
        r, c = divmod(i, cols)
        x, y = c * tileW, r * tileH
        sheet[y : y + 240, x : x + 320] = cv2.resize(frame, (320, 240))
        ok = read == case.stickers
        colour = (40, 150, 40) if ok else (30, 30, 200)
        label = f"{case.name}: {'PASS' if ok else 'FAIL'}" + (" (known)" if case.knownIssue and not ok else "")
        cv2.putText(sheet, label, (x + 6, y + 258), cv2.FONT_HERSHEY_SIMPLEX, 0.5, colour, 1, cv2.LINE_AA)
        if not ok:
            got = "no face found" if read is None else " ".join(n[0] for n in read)
            cv2.putText(sheet, f"got {got}", (x + 6, y + 275), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (60, 60, 60), 1)
    return sheet


if __name__ == "__main__":
    from rubiks_cube.scanner_utils import readFace

    outDir = sys.argv[1] if len(sys.argv) > 1 else os.path.join(os.path.dirname(__file__), "scanner_images")
    os.makedirs(outDir, exist_ok=True)
    results = []
    for case in CASES:
        frame = render(case)
        cv2.setRNGSeed(0)
        output = frame.copy()
        read = readFace(frame, SCAN_COLOURS, output)
        cv2.imwrite(os.path.join(outDir, f"{case.name}.png"), frame)
        cv2.imwrite(os.path.join(outDir, f"{case.name}_detected.png"), output)
        results.append((case, frame, read))
        print(f"{case.name:15} {'PASS' if read == case.stickers else 'FAIL'}  {case.description}")
    cv2.imwrite(os.path.join(outDir, "contact_sheet.png"), contactSheet(results))
    print(f"wrote {outDir}")
