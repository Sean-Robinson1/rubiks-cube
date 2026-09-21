import random
import unittest

from rubiks_cube.constants import STRING_ROTATION_MAPPINGS
from rubiks_cube.cube import Cube
from rubiks_cube.cube_utils import checkMask, combineMasks, formatDuration, optimiseMoves, rotate


class TestCubeNonSolver(unittest.TestCase):
    def test_combineMasks(self):
        mask1 = "." * 54
        mask2 = "R" * 54
        combined = combineMasks(mask1, mask2)
        self.assertEqual(combined, "R" * 54)
        combined2 = combineMasks(mask2, mask1)
        self.assertEqual(combined2, "R" * 54)

        mask3 = "W" * 9 + "." * 45
        mask4 = "." * 45 + "Y" * 9
        combined3 = combineMasks(mask3, mask4)
        self.assertEqual(combined3, "W" * 9 + "." * 36 + "Y" * 9)

        mask5 = "W" * 9 + "." * 45
        mask6 = "G" * 18 + "." * 36

        combined4 = combineMasks(mask5, mask6)
        self.assertEqual(combined4, "W" * 9 + "G" * 9 + "." * 36)

    def test_checkMask(self):
        mask = "R" * 54
        state = "R" * 54
        self.assertTrue(checkMask(mask, state))

        mask = "." * 54
        state = "G" * 54
        self.assertTrue(checkMask(mask, state))

        mask = "R" * 10 + "." * 44
        state = "R" * 10 + "G" * 44
        self.assertTrue(checkMask(mask, state))

        mask = "R" * 54
        state = "G" * 54
        self.assertFalse(checkMask(mask, state))

        mask = "R" * 53 + "G"
        state = "R" * 54
        self.assertFalse(checkMask(mask, state))

    def test_rotate(self):
        cube = Cube()
        for rotation in ["U", "U'", "D", "D'", "L", "L'", "R", "R'", "F", "F'", "B", "B'"]:
            original = str(cube)
            rotated = rotate(original, rotation)
            cube.executeSequence(rotation)
            self.assertEqual(rotated, str(cube))

    def test_rotationMappingsArePermutations(self):
        # every rotation mapping must be a genuine permutation of the 54 sticker positions - a typo
        # (a duplicated or missing index) would silently corrupt the cube, so guard the raw data
        for name, mapping in STRING_ROTATION_MAPPINGS.items():
            self.assertEqual(sorted(mapping), list(range(54)), f"{name} is not a permutation of 0..53")

        # and each clockwise mapping must be the exact inverse of its prime
        solved = str(Cube())
        for move in ["U", "D", "L", "R", "F", "B"]:
            self.assertEqual(rotate(rotate(solved, move), move + "'"), solved)

    def test_optimiseMoves(self):
        # a move followed by its inverse cancels; four-in-a-row cancels; three collapse to the inverse
        self.assertEqual(optimiseMoves(["R", "Ri"]), [])
        self.assertEqual(optimiseMoves(["U", "U", "U", "U"]), [])
        self.assertEqual(optimiseMoves(["U", "U", "U"]), ["Ui"])
        self.assertEqual(optimiseMoves(["Fi", "Fi", "Fi"]), ["F"])
        # unrelated moves, a lone move, and a trailing move after a cancellation are all preserved
        # (regression for a tail-drop bug that silently discarded the last move)
        self.assertEqual(optimiseMoves(["R", "U", "F"]), ["R", "U", "F"])
        self.assertEqual(optimiseMoves(["R"]), ["R"])
        self.assertEqual(optimiseMoves(["R", "Ri", "U"]), ["U"])

    def test_optimiseMovesPreservesTransformation(self):
        # optimised sequences must have the same net effect as the original and never be longer
        random.seed(0)
        faces = "RLUDFB"
        for _ in range(1000):
            sequence = [random.choice(faces) + random.choice(["", "i"]) for _ in range(random.randint(0, 12))]
            optimised = optimiseMoves(sequence)
            self.assertLessEqual(len(optimised), len(sequence))

            original = Cube()
            original.executeSequence("".join(sequence))
            reduced = Cube()
            reduced.executeSequence("".join(optimised))
            self.assertEqual(str(original), str(reduced))

    def test_wideKeyEncodeMatchesPerSlot(self):
        # the grouped wide-key encode must equal an independent slot-by-slot summation of the same
        # per-slot contributions, over real corner-stage and middle-stage states
        from rubiks_cube.corner_table import _CORNER_SLOT_LUT, _CORNER_STICKERS, encodeCorners
        from rubiks_cube.middle_table import _MIDDLE_SLOT_LUT, _MIDDLE_STICKERS, encodeMiddles

        def refCorners(state):
            c = _CORNER_STICKERS(state)
            return sum(_CORNER_SLOT_LUT[s].get((c[s * 3], c[s * 3 + 1], c[s * 3 + 2]), 0) for s in range(8))

        def refMiddles(state):
            m = _MIDDLE_STICKERS(state)
            return sum(_MIDDLE_SLOT_LUT[s].get((m[s * 2], m[s * 2 + 1]), 0) for s in range(8))

        random.seed(0)
        cube = Cube()
        for _ in range(3000):
            cube.randomise()
            cube.movesMade = []
            cube.solveCross()
            self.assertEqual(encodeCorners(cube.state), refCorners(cube.state))
            cube.solveF2LCorners()
            self.assertEqual(encodeMiddles(cube.state), refMiddles(cube.state))

    def test_formatDuration(self):
        self.assertEqual(formatDuration(45.0), "45 s")
        self.assertEqual(formatDuration(0.0163), "16.3 ms")
        self.assertEqual(formatDuration(7.07e-06), "7.07 us")
        self.assertEqual(formatDuration(1.5e-05), "15 us")
        self.assertEqual(formatDuration(5e-10), "0.5 ns")
        self.assertEqual(formatDuration(0.0), "0 ns")

        # a duration that would round up to 1000 of a unit steps up to the next one
        self.assertEqual(formatDuration(0.9999), "1 s")
        self.assertEqual(formatDuration(0.0009999), "1 ms")
        self.assertEqual(formatDuration(9.9999e-07), "1 us")

        # each unit boundary lands on the larger unit, not 1000 of the smaller
        self.assertEqual(formatDuration(1e-3), "1 ms")
        self.assertEqual(formatDuration(1e-6), "1 us")
        self.assertEqual(formatDuration(1e-9), "1 ns")


if __name__ == "__main__":
    unittest.main()
