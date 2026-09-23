import unittest

import numpy as np

from rubiks_cube.scanner_utils import extractCells


class TestScannerUtils(unittest.TestCase):
    def test_extractCellsNonSquare(self):
        # wider than it is tall, so swapping width and height would put windows in the wrong cells.
        # each cell is filled with its own index, so every window has to come back as one value
        h, w = 90, 150
        image = np.zeros((h, w, 3), dtype=np.uint8)
        for y in range(3):
            for x in range(3):
                image[y * h // 3 : (y + 1) * h // 3, x * w // 3 : (x + 1) * w // 3] = y * 3 + x

        cells = extractCells(image)
        self.assertEqual(len(cells), 9)
        for i, cell in enumerate(cells):
            self.assertGreater(cell.size, 0)
            self.assertTrue((cell == i).all(), f"cell {i} reads outside its square")


if __name__ == "__main__":
    unittest.main()
