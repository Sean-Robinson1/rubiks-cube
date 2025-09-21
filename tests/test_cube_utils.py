import unittest

from rubiks_cube.cube import Cube
from rubiks_cube.cube_utils import checkMask, combineMasks, rotate


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


if __name__ == "__main__":
    unittest.main()
