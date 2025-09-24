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


## Run tests / CI benchmark
Run the CI benchmark script (solves 1000 cubes and records solve information):
```bash
python tests/ci_test.py
```

> **Note** - The time for an average solve should be ~0.01 seconds


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
