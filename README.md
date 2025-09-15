# Rubik's Cube Solver and Scanner

This project provides a Rubik's Cube simulator, solver, 3D plotting, benchmarking scripts, and can scan a cube from a webcam video.  
It includes a `Cube` class for simulating and solving the cube, utilities for cube manipulation, and CI integration for automated testing and performance analysis.

## Features
- **Cube simulation:** create, randomise and manipulate cubes (Cube class).
- **Solver:** step-by-step solution routines and move optimisation.
- **3D plotting:** view cube state in an interactive Matplotlib/Tk window.
- **Scanner:** capture cube state from a webcam and interpret colours.
- **Benchmarking:** CI/locally runnable performance script (tests/ci_test.py).
- **Tooling:** pre-commit hooks (Black/isort/Ruff) and packaging via pyproject.toml.

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

## Run tests / CI benchmark
Run the CI benchmark script (solves 1000 cubes and records solve information):
```bash
python tests/ci_test.py
```

> **Note** - The time for an average solve should be ~0.01 seconds

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
- src/rubiks_cube/
  - __init__.py
  - main.py               — Entrypoint
  - gui.py                — Initialises and handles GUI logic
  - cube.py               — Cube class and solver logic
  - cube_utils.py         — Cube helper functions
  - cube_plotter.py       — 3D plotting utilities
  - cube_scanner.py       — Webcam scanner
  - dominant_colour.py    — Colour extraction helpers
  - constants.py          — Masks and constants
- tests/
  - ci_test.py            — CI benchmark
- .github/workflows/ci.yml — CI workflow
- pyproject.toml          — packaging and dependencies
- .pre-commit-config.yaml — formatting/lint hooks
- README.md, LICENSE, .gitignore

> **Note:** - cube.py contains most of the program's logic
