import random
import unittest

from rubiks_cube.constants import SOLVED_MASK
from rubiks_cube.cube import Cube
from rubiks_cube.cube_validation import CORNER_ORDER, EDGE_ORDER, validateCube


def scrambled(seed: int = 0) -> str:
    random.seed(seed)
    cube = Cube()
    cube.randomise()
    return cube.state


def swapped(state: str, a: tuple[int, ...], b: tuple[int, ...]) -> str:
    # move the piece in slot a to slot b and back, sticker for sticker in the order given
    s = list(state)
    for p, q in zip(a, b):
        s[p], s[q] = state[q], state[p]
    return "".join(s)


class TestValidateCube(unittest.TestCase):
    def test_realCubesPass(self):
        self.assertEqual(validateCube(SOLVED_MASK), [])
        random.seed(0)
        cube = Cube()
        for _ in range(2000):
            cube.randomise()
            self.assertEqual(validateCube(cube.state), [], cube.state)

    def test_twistedCorner(self):
        c = CORNER_ORDER[4]
        s = list(scrambled())
        s[c[0]], s[c[1]], s[c[2]] = s[c[2]], s[c[0]], s[c[1]]
        problems = validateCube("".join(s))
        self.assertEqual(len(problems), 1)
        self.assertIn("corner is twisted", problems[0])

    def test_flippedEdge(self):
        ref, other = EDGE_ORDER[7]
        s = list(scrambled())
        s[ref], s[other] = s[other], s[ref]
        problems = validateCube("".join(s))
        self.assertEqual(len(problems), 1)
        self.assertIn("edge is flipped", problems[0])

    def test_swappedEdges(self):
        problems = validateCube(swapped(scrambled(), EDGE_ORDER[0], EDGE_ORDER[5]))
        self.assertEqual(len(problems), 1)
        self.assertIn("swapped", problems[0])

    def test_swappingTwoCornersAndTwoEdgesIsLegal(self):
        # parity only has to match between corners and edges, so this is a real cube
        state = swapped(scrambled(), CORNER_ORDER[1], CORNER_ORDER[6])
        state = swapped(state, EDGE_ORDER[2], EDGE_ORDER[9])
        self.assertEqual(validateCube(state), [])

    def test_impossiblePiece(self):
        # trade a corner sticker for an edge sticker: the counts still hold but a corner reads G/G/O
        s = list(SOLVED_MASK)
        s[0], s[10] = s[10], s[0]
        problems = validateCube("".join(s))
        self.assertTrue(any("isn't a real piece" in p for p in problems), problems)

    def test_wrongCounts(self):
        s = list(SOLVED_MASK)
        s[0] = "R"
        problems = validateCube("".join(s))
        self.assertEqual(len(problems), 1)
        self.assertIn("9 times", problems[0])

    def test_centresSwapped(self):
        s = list(SOLVED_MASK)
        s[13], s[22] = s[22], s[13]
        self.assertIn("centre", validateCube("".join(s))[0])

    def test_solverGivesNothingForWhatThisCatches(self):
        # the misscan that used to reach the GUI as "(no moves)": one yellow corner twisted in place
        s = list(SOLVED_MASK)
        s[15], s[44], s[51] = s[44], s[51], s[15]
        state = "".join(s)
        cube = Cube(state)
        cube.movesMade = []
        cube.solve()
        self.assertFalse(cube.isSolved)
        self.assertTrue(validateCube(state))


if __name__ == "__main__":
    unittest.main()
