"""Synthetic webcam frames of a cube face, for testing readFace without a camera.

Run it to write every case out as pngs, split into passed/ and failed/, plus a contact sheet and a
summary.txt of what readFace made of them:

    python tests/scanner_images.py [outdir] [--standard]

--standard draws the stickers in STANDARD_RGB instead of the SCAN_COLOURS camera's colours, and
writes to scanner_images_standard/ by default. The knownIssue notes are written for the default
palette, so they're dropped there.

pngs are gitignored, so the tests build the frames in memory instead of loading files.
"""

import os
import sys
from dataclasses import dataclass, field, replace

import cv2
import numpy as np

from rubiks_cube.constants import SCAN_COLOURS

FRAME_W, FRAME_H = 640, 480

# where the script writes its output, and where the tests refresh summary.txt
DEFAULT_DIR = os.path.join(os.path.dirname(__file__), "scanner_images")

# stickers as the camera behind SCAN_COLOURS saw them, so the baseline tests the pipeline rather
# than the reference values. RGB
STICKER_RGB = {name: tuple(int(round(v)) for v in rgb) for name, rgb in SCAN_COLOURS}

# commonly quoted colours for a standard cube, RGB
STANDARD_RGB = {
    "White": (255, 255, 255),
    "Yellow": (255, 213, 0),
    "Red": (183, 18, 52),
    "Orange": (255, 88, 0),
    "Blue": (0, 70, 173),
    "Green": (0, 155, 72),
}

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
    Case("tilt10", "rotated 10 degrees", rotation=10),
    Case("tilt30", "rotated 30 degrees", rotation=30, knownIssue="face crop is an axis aligned box"),
    Case("perspective", "viewed from slightly below", skew=0.15),
    Case("dim", "dark room", brightness=0.45, knownIssue="fixed RGB references, nothing normalises brightness"),
    Case(
        "bright", "overexposed", brightness=1.35, knownIssue="fixed RGB references, washed out yellow is nearer white"
    ),
    Case(
        "warmLight",
        "tungsten bulb colour cast",
        tint=(1.15, 1.0, 0.7),
        knownIssue="fixed RGB references, nothing corrects white balance",
    ),
    Case("glare", "specular highlight across the stickers", glare=170),
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


def drawReading(output: np.ndarray, case: Case, read: list[str] | None) -> None:
    """Draws what readFace read next to what it should have, bottom left, crossing out wrong stickers."""
    from rubiks_cube.constants import USUAL_COLOUR_VALUES

    cell, pad = 22, 10
    grid = cell * 3
    x0, y0 = pad, FRAME_H - grid - 44
    cv2.rectangle(output, (x0 - 6, y0 - 22), (x0 + 2 * grid + pad + 6, FRAME_H - 6), (245, 245, 245), -1)
    for gx, title, names in ((x0, "read", read), (x0 + grid + pad, "want", case.stickers)):
        cv2.putText(output, title, (gx, y0 - 7), cv2.FONT_HERSHEY_SIMPLEX, 0.45, (30, 30, 30), 1, cv2.LINE_AA)
        if names is None:
            cv2.putText(output, "no face", (gx, y0 + 35), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (30, 30, 200), 1, cv2.LINE_AA)
            continue
        for i, name in enumerate(names):
            row, col = divmod(i, 3)
            x, y = gx + col * cell, y0 + row * cell
            cv2.rectangle(output, (x, y), (x + cell - 2, y + cell - 2), USUAL_COLOUR_VALUES[name], -1)
            cv2.putText(output, name[0], (x + 3, y + 15), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 0, 0), 1, cv2.LINE_AA)
            if names is read and name != case.stickers[i]:
                # small badge in the corner, so the colour underneath stays readable
                bx, by, b = x + cell - 9, y, 7
                cv2.rectangle(output, (bx, by), (bx + b, by + b), (255, 255, 255), -1)
                cv2.line(output, (bx + 1, by + 1), (bx + b - 1, by + b - 1), (0, 0, 0), 1)
                cv2.line(output, (bx + b - 1, by + 1), (bx + 1, by + b - 1), (0, 0, 0), 1)
    ok = read == case.stickers
    verdict = "PASS" if ok else "FAIL" + (" (known)" if case.knownIssue else "")
    cv2.putText(
        output,
        verdict,
        (x0, FRAME_H - 14),
        cv2.FONT_HERSHEY_SIMPLEX,
        0.5,
        (40, 150, 40) if ok else (30, 30, 200),
        1,
        cv2.LINE_AA,
    )


def summaryText(results: list[tuple[Case, list[str] | None]]) -> str:
    """Aggregate numbers for a run: outcomes, sticker accuracy, a colour confusion table, then each case."""
    names = [name for name, _ in SCAN_COLOURS]
    confusion = {want: {got: 0 for got in names} for want in names}
    exact = wrong = noFace = right = total = 0
    lines = []
    for case, read in results:
        if read is None:
            noFace += 1
            got = "no face found"
            nRight = 0
        else:
            nRight = sum(w == g for w, g in zip(case.stickers, read))
            right += nRight
            total += 9
            for w, g in zip(case.stickers, read):
                confusion[w][g] += 1
            if read == case.stickers:
                exact += 1
                got = ""
            else:
                wrong += 1
                got = ", ".join(f"{w}->{g}" for w, g in zip(case.stickers, read) if w != g)
        verdict = "PASS" if read == case.stickers else ("FAIL (known)" if case.knownIssue else "FAIL")
        lines.append(f"{case.name:14} {verdict:13} {nRight}/9  {got}")
        if case.knownIssue and read != case.stickers:
            lines.append(f"{'':29}known: {case.knownIssue}")

    n = len(results)
    out = [
        f"{n} cases",
        f"  exact match        {exact:3}  ({exact / n:.0%})",
        f"  wrong reading      {wrong:3}  ({wrong / n:.0%})  <- a face came back with wrong colours",
        f"  no face found      {noFace:3}  ({noFace / n:.0%})",
        f"sticker accuracy     {right}/{total} ({right / max(total, 1):.1%}) over faces that were found",
        "",
        "confusion: rows are the real colour, columns what it was read as (found faces only)",
        f"{'':9}" + "".join(f"{g[:6]:>8}" for g in names),
    ]
    for w in names:
        out.append(f"{w:9}" + "".join(f"{confusion[w][g] or '.':>8}" for g in names))
    out += ["", "per case"] + lines
    return "\n".join(out) + "\n"


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

    args = [a for a in sys.argv[1:] if a != "--standard"]
    standard = "--standard" in sys.argv[1:]
    defaultDir = DEFAULT_DIR + "_standard" if standard else DEFAULT_DIR
    outDir = args[0] if args else defaultDir
    cases = CASES
    if standard:
        # only cases drawn in the default palette switch, otherCamera keeps its own
        cases = [
            replace(c, knownIssue="", palette=STANDARD_RGB if c.palette is STICKER_RGB else c.palette) for c in CASES
        ]
    dirs = {True: os.path.join(outDir, "passed"), False: os.path.join(outDir, "failed")}
    for d in dirs.values():
        os.makedirs(d, exist_ok=True)
    # a case can change folder between runs, so clear what earlier runs wrote (including the old flat
    # layout, where the case images sat at the top level)
    for case in cases:
        for d in (outDir, *dirs.values()):
            for suffix in ("", "_detected"):
                path = os.path.join(d, f"{case.name}{suffix}.png")
                if os.path.exists(path):
                    os.remove(path)

    results = []
    for case in cases:
        frame = render(case)
        output = frame.copy()
        read = readFace(frame, SCAN_COLOURS, output)
        drawReading(output, case, read)
        caseDir = dirs[read == case.stickers]
        cv2.imwrite(os.path.join(caseDir, f"{case.name}.png"), frame)
        cv2.imwrite(os.path.join(caseDir, f"{case.name}_detected.png"), output)
        results.append((case, frame, read))
        print(f"{case.name:15} {'PASS' if read == case.stickers else 'FAIL'}  {case.description}")
    cv2.imwrite(os.path.join(outDir, "contact_sheet.png"), contactSheet(results))
    with open(os.path.join(outDir, "summary.txt"), "w", encoding="utf-8") as handle:
        handle.write(summaryText([(case, read) for case, _, read in results]))
    print(f"wrote {outDir}")
