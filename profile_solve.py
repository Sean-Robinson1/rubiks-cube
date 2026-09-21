"""Detailed profiling harness for the Rubik's cube solver.

Run it to see where solve time goes: per-function call counts, internal vs cumulative time, and each
function's share of the total. Scrambles are generated up front so randomise() isn't measured (unless
you pass --scramble).

Examples:
    python profile_solve.py                 # 2000 solves, top 30 functions by internal time
    python profile_solve.py --solves 5000   # more solves = steadier numbers
    python profile_solve.py --sort cumtime   # order by cumulative time (top-down view)
    python profile_solve.py --top 50 --all   # show 50 rows, include everything (not just hot ones)
    python profile_solve.py --scramble       # also profile the scrambling

Columns:
    ncalls      how many times the function was called (total, across all solves)
    per solve   ncalls / number of solves
    tottime     internal time in the function itself (excludes time in things it calls)
    %tot        that function's share of total internal time  <-- "what percent of time is spent where"
    cumtime     cumulative time (includes everything it calls)
    us/call     tottime per call, in microseconds
"""

import argparse
import cProfile
import os
import pstats
import random
import sys
import time

try:
    from rubiks_cube import Cube
except ModuleNotFoundError:  # run straight from a source checkout without installing
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "src"))
    from rubiks_cube import Cube

STAGES = ["solveCross", "solveF2LCorners", "solveF2LMiddlePieces", "solveLastLayer"]


def _isBuiltin(func) -> bool:
    """Checks whether a profiled function is a C or built-in function.

    pstats keys those with a '~' filename and a line number of 0.

    Args:
        func (tuple): The (filename, line number, name) key pstats uses.

    Returns:
        bool: True if the function is a built-in, False otherwise.
    """
    filename, lineno, _ = func
    return not filename or filename == "~" or lineno == 0


def _formatFunc(func) -> str:
    """Turns a pstats function key into a short readable label.

    Args:
        func (tuple): The (filename, line number, name) key pstats uses.

    Returns:
        str: The label to print for the function.
    """
    filename, lineno, name = func
    if _isBuiltin(func):
        return name  # a built-in / C function, e.g. <method 'join' of 'str' objects>
    return f"{os.path.basename(filename)}:{lineno}({name})"


def wallClockSummary(cube: Cube, scrambles: list) -> None:
    """Times the solves without the profiler attached and prints the totals.

    Args:
        cube (Cube): The cube to solve with.
        scrambles (list): The scrambled states to solve.
    """
    solves = len(scrambles)

    # timed per solve, with the state setup left outside the clock, so this matches what
    # Cube.analyseSolves reports. Timing the loop as a whole instead charges the two attribute
    # writes and the loop machinery to the solver, which reads about 0.5us a solve too high.
    total = 0.0
    for state in scrambles:
        cube.state = state
        cube.movesMade = []
        tick = time.perf_counter()
        cube.solve()
        total += time.perf_counter() - tick

    stageTime = {stage: 0.0 for stage in STAGES}
    for state in scrambles:
        cube.state = state
        cube.movesMade = []
        for stage in STAGES:
            tick = time.perf_counter()
            getattr(cube, stage)()
            stageTime[stage] += time.perf_counter() - tick

    print("\n=== wall clock (no profiler overhead, solve() only) ===")
    print(f"  {solves} solves in {total:.4f}s  ->  {total / solves * 1e6:.2f} us/solve")
    print("  per stage (us/solve, share of solve):")
    perStageTotal = sum(stageTime.values()) or 1.0
    for stage in STAGES:
        us = stageTime[stage] / solves * 1e6
        print(f"    {stage:22s} {us:8.2f} us   {stageTime[stage] / perStageTotal * 100:5.1f}%")


def profileSummary(cube: Cube, scrambles: list, includeScramble: bool, sortKey: str, top: int, showAll: bool) -> None:
    """Profiles the solves and prints a table of where the time goes.

    Args:
        cube (Cube): The cube to solve with.
        scrambles (list): The scrambled states to solve.
        includeScramble (bool): If True, randomise() is profiled alongside solve().
        sortKey (str): The column to sort the table by, either tottime or cumtime.
        top (int): The number of functions to list.
        showAll (bool): If True, lists every function rather than just the hot path.
    """

    def run():
        for state in scrambles:
            if includeScramble:
                cube.randomise()
            else:
                cube.state = state
            cube.movesMade = []
            cube.solve()

    profiler = cProfile.Profile()
    profiler.enable()
    run()
    profiler.disable()

    stats = pstats.Stats(profiler)
    entries = stats.stats  # {func: (primitive_calls, total_calls, tottime, cumtime, callers)}
    totalTottime = sum(v[2] for v in entries.values()) or 1.0
    totalCalls = sum(v[1] for v in entries.values())
    solves = len(scrambles)

    rows = []
    for func, (_pc, ncalls, tottime, cumtime, _callers) in entries.items():
        label = _formatFunc(func)
        # default (non --all) view: keep the solver's own functions and the C primitives they call
        # (join, dict.get, itemgetter), dropping stdlib/harness noise and the profiler's own frames
        if not showAll and "rubiks_cube" not in (func[0] or "") and not _isBuiltin(func):
            continue
        if not showAll and "_lsprof" in label:
            continue
        rows.append((tottime, cumtime, ncalls, label))

    rows.sort(key=lambda r: (r[1] if sortKey == "cumtime" else r[0]), reverse=True)

    print(f"\n=== cProfile ({solves} solves, {totalCalls} total calls, sorted by {sortKey}) ===")
    print("  NOTE: cProfile adds per-call overhead, so these times are inflated vs the wall clock above;")
    print("        use them for relative shares and call counts, not absolute timing.")
    print(f"  {'ncalls':>9} {'per solve':>9} {'tottime':>9} {'%tot':>6} {'cumtime':>9} {'us/call':>8}  function")
    for tottime, cumtime, ncalls, label in rows[:top]:
        perSolve = ncalls / solves
        pct = tottime / totalTottime * 100
        usCall = tottime / ncalls * 1e6 if ncalls else 0.0
        print(f"  {ncalls:>9} {perSolve:>9.2f} {tottime:>9.4f} {pct:>5.1f}% {cumtime:>9.4f} {usCall:>8.3f}  {label}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Profile the Rubik's cube solver.")
    parser.add_argument("--solves", type=int, default=2000, help="number of solves to profile (default 2000)")
    parser.add_argument("--top", type=int, default=30, help="number of functions to list (default 30)")
    parser.add_argument("--sort", choices=["tottime", "cumtime"], default="tottime", help="sort order")
    parser.add_argument("--all", action="store_true", help="show all functions, not just the hot path")
    parser.add_argument("--scramble", action="store_true", help="also profile randomise() (not just solve)")
    parser.add_argument("--seed", type=int, default=0, help="RNG seed for reproducible scrambles")
    args = parser.parse_args()

    random.seed(args.seed)
    cube = Cube()
    scrambles = []
    for _ in range(args.solves):
        cube.randomise()
        scrambles.append(cube.state)

    print(f"Profiling {args.solves} solves (seed={args.seed}, scramble profiled={args.scramble})")
    wallClockSummary(cube, scrambles)
    profileSummary(cube, scrambles, args.scramble, args.sort, args.top, args.all)


if __name__ == "__main__":
    main()
