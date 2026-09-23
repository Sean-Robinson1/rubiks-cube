import random
import unittest

from rubiks_cube import corner_table, last_layer_table, middle_table
from rubiks_cube.constants import SOLVED_MASK
from rubiks_cube.corner_table import CORNER_PATHS
from rubiks_cube.cross_table import CROSS_PATHS
from rubiks_cube.cube import Cube
from rubiks_cube.cube_utils import applyMoveLabels
from rubiks_cube.last_layer_table import LAST_LAYER_PATHS
from rubiks_cube.middle_table import MIDDLE_PATHS

# 54 distinct stickers, so a permutation can't pass by swapping two of the same colour
PROBE = "".join(chr(0x100 + i) for i in range(54))

# stickers that have to be solved once each stage is done. each stage's successor preserves exactly
# the pieces placed so far, so its preserved set doubles as the stage's postcondition
CROSS_DONE = corner_table.PRESERVED_STICKERS
CORNERS_DONE = middle_table.PRESERVED_STICKERS
F2L_DONE = last_layer_table._NON_LL


def scrambles(n: int, seed: int = 0) -> list[str]:
    random.seed(seed)
    cube = Cube()
    out = []
    for _ in range(n):
        cube.randomise()
        out.append(cube.state)
    return out


def solvedAt(state: str, stickers: list[int]) -> bool:
    return all(state[i] == SOLVED_MASK[i] for i in stickers)


class TestSolver(unittest.TestCase):
    def test_replayedSolutionsSolve(self):
        # isSolved after solve() proves little, solveLastLayer sets SOLVED_MASK without applying
        # anything. replaying the reported moves on the scramble is the real check
        cube = Cube()
        for scramble in scrambles(3000):
            cube.state = scramble
            cube.movesMade = []
            cube.solve()
            self.assertEqual(applyMoveLabels(scramble, cube.movesMade), SOLVED_MASK, scramble)

    def test_stagePostconditions(self):
        # each stage leaves everything placed so far solved, and solve() matches the four stage
        # methods run in turn (solve() inlines them, so the two could drift apart)
        cube = Cube()
        for scramble in scrambles(1000, seed=1):
            cube.state = scramble
            cube.movesMade = []
            cube.solve()
            expected = cube.movesMade

            cube.state = scramble
            cube.movesMade = []
            cube.solveCross()
            self.assertTrue(solvedAt(cube.state, CROSS_DONE), scramble)
            cube.solveF2LCorners()
            self.assertTrue(solvedAt(cube.state, CORNERS_DONE), scramble)
            cube.solveF2LMiddlePieces()
            self.assertTrue(solvedAt(cube.state, F2L_DONE), scramble)
            cube.solveLastLayer()
            self.assertTrue(cube.isSolved, scramble)
            self.assertEqual(list(cube.movesMade), list(expected), scramble)

    def test_tableSizes(self):
        # catches a missing or truncated .bin, which now loads as an empty table rather than failing
        for name, paths, size, entries in (
            ("cross", CROSS_PATHS, 24**4, 190079),
            ("corners", CORNER_PATHS, 24**4, 136079),
            ("middles", MIDDLE_PATHS, 16**4, 26879),
        ):
            self.assertEqual(len(paths), size, name)
            self.assertEqual(sum(1 for e in paths if e is not None), entries, name)
        # every reachable last layer bar the solved one
        self.assertEqual(len(LAST_LAYER_PATHS), 62207)

    def test_pathPermutationsMatchLabels(self):
        # the solver applies the stored permutation but reports the labels, so the two have to agree
        # for every entry, not just the ones random scrambles happen to hit
        for name, paths in (("cross", CROSS_PATHS), ("corners", CORNER_PATHS), ("middles", MIDDLE_PATHS)):
            for index, entry in enumerate(paths):
                if entry is None:
                    continue
                permutation, labels = entry
                gathered = "".join(PROBE[i] for i in permutation)
                self.assertEqual(gathered, applyMoveLabels(PROBE, list(labels)), f"{name} entry {index}")


if __name__ == "__main__":
    unittest.main()
