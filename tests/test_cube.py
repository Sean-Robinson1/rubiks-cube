import unittest

from rubiks_cube.constants import SOLVED_MASK
from rubiks_cube.cube import Cube


class TestCubeNonSolver(unittest.TestCase):
    def test_str(self):
        cube = Cube()
        self.assertTrue(str(cube) == SOLVED_MASK)

        cube = Cube("ORBRWYYGRWBROGYYGOGYWORBYROGBRWBOBRWYGGWOBBGGBYWOYWOWR")
        self.assertTrue(str(cube) == "ORBRWYYGRWBROGYYGOGYWORBYROGBRWBOBRWYGGWOBBGGBYWOYWOWR")

    def test_repr(self):
        cube = Cube()

        for _ in range(10):
            cube.randomise()
            r = repr(cube)
            self.assertTrue(r == f"Cube('{str(cube)}')")

    def test_getitem(self):
        cube = Cube()
        for i in range(6):
            face = cube[i]
            self.assertEqual(face, cube.faces[i])

    def test_calculateFaces(self):
        cube = Cube()
        cube.calculateFaces("R", "W")
        self.assertEqual(cube.front, "R")
        self.assertEqual(cube.top, "W")
        self.assertEqual(cube.bottom, cube.getOppositeFace("W"))
        self.assertEqual(cube.back, cube.getOppositeFace("R"))
        self.assertEqual(cube.left, cube.getLeftFace("R"))
        self.assertEqual(cube.right, cube.getRightFace("R"))

        cube = Cube()
        cube.calculateFaces("W", "B")
        self.assertEqual(cube.front, "W")
        self.assertEqual(cube.top, "B")
        self.assertEqual(cube.bottom, "G")
        self.assertEqual(cube.back, "Y")
        self.assertEqual(cube.left, "O")
        self.assertEqual(cube.right, "R")

        cube = Cube()
        cube.calculateFaces("R", "Y")
        self.assertEqual(cube.front, "R")
        self.assertEqual(cube.top, "Y")
        self.assertEqual(cube.bottom, "W")
        self.assertEqual(cube.back, "O")
        self.assertEqual(cube.left, "B")
        self.assertEqual(cube.right, "G")

        cube = Cube()
        cube.calculateFaces("R", "B")
        self.assertEqual(cube.front, "R")
        self.assertEqual(cube.top, "B")
        self.assertEqual(cube.bottom, "G")
        self.assertEqual(cube.back, "O")
        self.assertEqual(cube.left, "W")
        self.assertEqual(cube.right, "Y")

    def test_randomiseCube(self):
        cube = Cube()
        moves = cube.randomise()
        self.assertIsInstance(moves, list)
        self.assertTrue(len(moves) > 0)

        states = set()
        for _ in range(100):
            cube.randomise()
            states.add(str(cube))
        self.assertTrue(len(states) == 100)

    def test_workBackwards(self):
        cube = Cube()
        moves = cube.randomise()
        cube.workBackwards(moves)
        self.assertTrue(cube.isSolved)

    def test_rotate_methods(self):
        cube = Cube()
        cube.rotateU()
        cube.rotateD()
        cube.rotateF()
        cube.rotateB()
        cube.rotateR()
        cube.rotateL()
        self.assertTrue(str(cube) == "GBBGWBGGBWWWOGRYYYOROWRYOROWWWRBOYYYRORWOYRORGBBGYBGGB")

    def test_executeSequence(self):
        cube1 = Cube()
        cube2 = Cube()
        sequence = "RUR'U'FBUDLiRiUiDi"

        cube1.executeSequence(sequence)

        moveMap = {
            "R": cube2.rotateR,
            "L": cube2.rotateL,
            "U": cube2.rotateU,
            "D": cube2.rotateD,
            "F": cube2.rotateF,
            "B": cube2.rotateB,
        }
        i = 0
        while i < len(sequence):
            ch = sequence[i]
            if ch not in moveMap:
                i += 1
                continue
            func = moveMap[ch]
            direction = True
            j = i + 1
            if j < len(sequence) and sequence[j] in ("'", "i"):
                direction = False
                j += 1
            func(direction)
            i = j

        self.assertEqual(str(cube1), str(cube2))

    def test_checkMask(self):
        cube = Cube()
        self.assertTrue(SOLVED_MASK)
        self.assertTrue(cube.checkMask("." * 54))
        self.assertFalse(cube.checkMask("." * 53 + "G"))

        cube.randomise()
        self.assertTrue(cube.checkMask("." * 54))

    def test_solve(self):
        cube = Cube()
        cube.randomise()
        cube.solve()
        self.assertTrue(cube.isSolved)


if __name__ == "__main__":
    unittest.main()
