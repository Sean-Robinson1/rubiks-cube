# Rubik's Cube Solver and Scanner

This project provides a Rubik's Cube simulator, solver, 3D plotting, benchmarking scripts, and can scan a cube from a webcam video.  
It includes a `Cube` class for simulating and solving the cube, utilities for cube manipulation, and CI integration for automated testing and performance analysis.

## Features

- **Cube Simulation:** Create, randomize, and manipulate Rubik's Cubes.
- **Solver:** Step-by-step solution algorithms for the cube.
- **Analysis:** Benchmark solver performance over multiple solves.
- **3D Plotting:** Visualise cube states.
- **Scanner:** Capture and interpret cube states from camera input.
- **CI Integration:** Automated analysis and testing via GitHub Actions.

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/Sean-Robinson1/rubiks_cube.git
   cd rubiks_cube
   ```
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

## Usage

### Solve and Analyse

Run the main simulation program:
```
python cube.py
```

### Run CI Benchmark

To benchmark 1000 solves and print analysis (used in CI):
```
python ci_test.py
```

### Scanner

To run the webcam scanner
```
python cube_scanner.py
```

## Project Structure

- `cube.py` — Main Cube class and solver logic
- `cube_utils.py` — Utility functions for cube manipulation
- `cube_plotter.py` — 3D plotting functions
- `ci_test.py` — CI benchmark script (see above)
- `cube_scanner.py` — Cube scanner
- `dominant_colour.py` - Extracts the dominant colour from an image, used for the scanner.
- `.github/workflows/ci.yml` — GitHub Actions workflow for CI


## Requirements

- Python 3.11+
- See `requirements.txt` for required packages
