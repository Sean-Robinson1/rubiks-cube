# Rubik's Cube Solver and Scanner

This project provides a Rubik's Cube simulator, solver, 3D plotting, benchmarking scripts, and can scan a cube from a webcam video.  
It includes a `Cube` class for simulating and solving the cube, utilities for cube manipulation, and CI integration for automated testing and performance analysis.

## Features
- **Cube simulation:** create, randomise and manipulate cubes (`Cube` class).
- **Solver:** step-by-step solution routines and move optimisation.
- **3D plotting:** view cube state in an interactive Matplotlib/Tk window.
- **Scanner:** capture cube state from a webcam and interpret colours.
- **Benchmarking:** CI/locally runnable performance script (`tests/ci_test.py`).
- **Tooling:** pre-commit hooks (Black/isort/Ruff) and packaging via `pyproject.toml`.

## Installation
1. Clone and cd into directory
```bash
git clone https://github.com/Sean-Robinson1/rubiks-cube
cd rubiks_cube
```

2. Create and activate a virtual environment:
```bash
python -m venv .venv
```

2. Install the project and dependencies:
```bash
pip install -e .
```

3. Run the application:
```bash   
python -m rubiks_cube.main
# or, if an entry-point script is installed:
rubiks-cube
```

## Usage

- **Cube Manipulation**
  - Rotate the cube using the on-screen buttons. Rotations are automatically applied based on the current orientation.
  - Click `Scramble` to randomise the cube.
  - Click `Reset View` to restore the default viewing angle.
  - Click `Animations: On/Off` to toggle whether there are visible animations when rotating the cube

- **Colour Calibration & Scanning**
  - Click `Calibrate Colours` to open the webcam. Hold a solved cube inside the rectangle and press the key matching the first letter of each colour to calibrate. This updates the internal colour detection. You will see the colours update in the top left. (As an example, if you want to calibrate the white colour hold the white face inside the rectangle and hold 'w')
  - Click `Scan Cube` to scan a cube using the webcam. Hold the cube up; it will be detected and scanned automatically. The scanned cube map will be displayed.

- **Solving**
  - Click `Solve` to compute the solution. A popup will show the moves required to solve the cube.

> Note there is current a minor issue if you try to rotate the cube while a face is already rotating - if the display becomes distorted then clicking `Reset View` should fix this. If not, turn animations off and make a rotation.

> The UI is designed to be intuitive. For best results, ensure your webcam is well-lit and the cube is clearly visible. Also if you have a reflective cube or one with text on it, this can affect the performance of the scanning.

## UI

Below is an image showing what the main UI window looks like:
<img width="600" height="400" alt="image" src="https://github.com/user-attachments/assets/a30d6f0b-7677-43f9-a598-bee95ec1171f" />


## Stats

| | |
|---|---|
| **Average solve** | **~7.8 us** |
| **Average solution** | **56.0 moves** (54.9 after `optimiseMoves`) |
| Longest solution seen | 70 moves |
| Throughput | ~128,000 cubes/second on one core |

Numbers from 3000 random scrambles on an idle machine. Scrambling is the slow part now:
`randomise()` does 50 separate face turns and comes out at roughly 5x the cost of a solve.

Each stage is one table lookup. The state gets encoded to an integer (the last layer skips even
that and keys straight off its 20 stickers), and the table hands back that stage's whole solution
as a single 54-square permutation plus the move labels. Nothing is searched at solve time.

### Solution length

| Stage | Mean moves | Worst case |
|---|---|---|
| Cross | 6.6 | 9 |
| F2L corners | 12.6 | 17 |
| F2L middles | 17.1 | 24 |
| Last layer | 19.7 | 29 |
| **Total** | **56.0** | **70** |
| After `optimiseMoves` | 54.9 | 68 |

It's a beginner method, so 56 moves is a long way off God's number of 20. Each stage is optimal for
the moves that stage is allowed to use, which isn't the same thing. The macros are enumerated
rather than written out by hand (see `macro_enumeration.py`), and that alone saved about 20 moves a
solve.

### Where the time goes

| Stage | Share of a solve |
|---|---|
| Cross | ~32% |
| F2L corners | ~30% |
| F2L middles | ~26% |
| Last layer | ~13% |

Don't read too much into the absolute times. The same code measured 7.9 us on an idle machine and
25 us with a browser open, so run it yourself rather than trusting the table above. The per-stage
numbers come from a second pass that calls the four stage methods one at a time, which costs more
than `solve()` does, so they won't add up to the total. They're only really useful against each
other.

### Tables

| Stage | States with a stored solution |
|---|---|
| Cross | 190,079 |
| F2L corners | 136,079 |
| F2L middles | 26,879 |
| Last layer | 62,207 |
| **Total** | **415,244** |

29.4 MB on disk, 26.8 MB of that being the path tables the solver actually reads. They take ~1.4 s
to load and sit at about 365 MB once they're up. That's the trade being made: a lot of memory so
there's no search at solve time.

## Run tests / CI benchmark
Run the CI benchmark script (solves 3000 cubes and records solve information):
```bash
python tests/ci_test.py
```

For a breakdown of where the time goes, with per-function call counts and internal time, use the
profiling harness:
```bash
python profile_solve.py --solves 3000
```

> **Note** - the average solve time it reports should be single-digit microseconds. See [Stats](#stats).


To run the unit tests:
```bash
# if pytest is not installed
pip install pytest

pytest tests/
```

## Formatting & pre-commit
This repo uses `black`, `isort` and `ruff` via `.pre-commit-config.yaml`.

Install hooks and format:
```powershell
pip install pre-commit
pre-commit install
pre-commit run --all-files
```

CI runs the same checks; the job will fail if the repo is not formatted according to rules.

## Repository layout
- `src/rubiks_cube/`
  - `__init__.py`
  - `main.py`                — Entrypoint
  - `gui.py`                 — Initialises and handles GUI logic
  - `cube.py`                — Cube class and solver logic
  - `cube_utils.py`          — Cube helper functions
  - `cube_plotter.py`        — 3D plotting utilities
  - `cube_scanner.py`        — Webcam scanner
  - `colour_calibration.py`  — Colour calibration GUI for webcam scanning
  - `constants.py`           — Masks and constants
  - `plotter_utils.py`       — Plotting helper functions
  - `scanner_utils.py`       — Scanning helper functions
- `tests/`
  - `ci_test.py`             — CI benchmark
  - `test_cube_utils.py`     — Cube utility tests
  - `test_cube.py`           — Cube tests 
- `.github/workflows/ci.yml` — CI workflow
- `pyproject.toml`           — packaging and dependencies
- `.pre-commit-config.yaml`  — formatting/lint hooks
- `README.md`, `LICENSE`, `.gitignore`, `requirements.txt`

> **Note:** - `cube.py` contains most of the program's logic
