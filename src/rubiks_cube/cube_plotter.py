import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .constants import AXIS_MAP, CENTER_ORDERINGS, FACE_CENTER_POSITIONS

COLOURS = ["White", "Yellow", "Red", "Orange", "Blue", "Green"]
colours = []
for colour in COLOURS:
    colours += [colour] * 9


def getDistance(a: np.ndarray, b: np.ndarray) -> float:
    """Calculate the Euclidean distance between two points.

    Args:
        a (np.ndarray): First point.
        b (np.ndarray): Second point.

    Returns:
        float: The Euclidean distance between the two points.
    """
    return np.sqrt(np.sum((a - b) ** 2))


def rotationMatrix(axis: np.ndarray, theta: float) -> np.ndarray:
    """Return the rotation matrix associated with rotation about the given axis by theta radians.

    Args:
        axis (np.ndarray): The axis to rotate about.
        theta (float): The angle to rotate by, in radians.

    Returns:
        np.ndarray: The rotation matrix.
    """
    axis = np.asarray(axis, dtype=float)
    axis = axis / np.linalg.norm(axis)
    a = np.cos(theta / 2.0)
    b, c, d = -axis * np.sin(theta / 2.0)
    return np.array(
        [
            [a * a + b * b - c * c - d * d, 2 * (b * c - a * d), 2 * (b * d + a * c)],
            [2 * (b * c + a * d), a * a + c * c - b * b - d * d, 2 * (c * d - a * b)],
            [2 * (b * d - a * c), 2 * (c * d + a * b), a * a + d * d - b * b - c * c],
        ]
    )


def rotatePlanes(planes: list[dict], indices: list[int], axis: np.ndarray, angle: float, center: np.ndarray) -> None:
    """Rotate the specified planes around a given axis by a certain angle.

    Args:
        planes (list[dict]): List of plane dicts to rotate.
        indices (list[int]): Indices of planes to rotate.
        axis (np.ndarray): Axis to rotate around.
        angle (float): Angle to rotate by, in radians.
        center (np.ndarray): Center point to rotate around.
    """
    R = rotationMatrix(axis, angle)
    for i in indices:
        corners = planes[i]["corners"] - center
        corners = corners @ R.T
        planes[i]["corners"] = corners + center
        planes[i]["center"] = (planes[i]["center"] - center) @ R.T + center


class CubePlotter:
    def __init__(self):
        self.planes = []
        self.fig, self.ax = None, None
        self.createFig()

    def createFig(self):
        """Creates a 3D fig and ax.

        Returns:
            tuple[plt.Figure, Axes3D]: The figure and 3D axis.
        """
        self.fig, self.ax = plt.subplots(subplot_kw={"projection": "3d"})

    def makePlane(
        self, xmin: float, xmax: float, ymin: float, ymax: float, zmin: float, zmax: float, colour: str
    ) -> dict:
        """Create a plane dict given its bounding box.

        Args:
            xmin (float): Minimum x-coordinate.
            xmax (float): Maximum x-coordinate.
            ymin (float): Minimum y-coordinate.
            ymax (float): Maximum y-coordinate.
            zmin (float): Minimum z-coordinate.
            zmax (float): Maximum z-coordinate.
            colour (str): Colour of the plane.

        Returns:
            dict: A dictionary representing the plane with keys "center", "corners", and "colour".
        """
        if xmin == xmax:
            center = np.array([xmin, (ymin + ymax) / 2, (zmin + zmax) / 2])
            corners = np.array([[xmin, ymin, zmin], [xmax, ymax, zmin], [xmax, ymax, zmax], [xmin, ymin, zmax]])
        elif ymin == ymax:
            center = np.array([(xmin + xmax) / 2, ymin, (zmin + zmax) / 2])
            corners = np.array([[xmin, ymin, zmin], [xmax, ymax, zmin], [xmax, ymax, zmax], [xmin, ymin, zmax]])
        else:
            center = np.array([(xmin + xmax) / 2, (ymin + ymax) / 2, zmin])
            corners = np.array([[xmin, ymin, zmin], [xmax, ymin, zmin], [xmax, ymax, zmax], [xmin, ymax, zmax]])

        return {"center": center, "corners": corners, "colour": colour}

    def plotRubiks3D(self, colours: list[list[str]]) -> tuple[plt.Figure, Axes3D, list[dict]]:
        """Create plane data for a Rubik's Cube and plot them.

        Args:
            colours (list[list[str]]): A flat list (length 54) of facelet colours.

        Returns:
            tuple[plt.Figure, Axes3D, list[dict]]: The figure, axis, and list of plane dicts.
        """
        self.planes = []
        counter = 0
        self.ax.cla()

        # Faces perpendicular to z-axis (White/Yellow)
        for z in [0, 3]:
            for i in range(3):
                for j in range(3):
                    self.planes.append(
                        self.makePlane(xmin=i, xmax=i + 1, ymin=j, ymax=j + 1, zmin=z, zmax=z, colour=colours[counter])
                    )
                    counter += 1

        # Faces perpendicular to x-axis (Red/Orange)
        for x in [0, 3]:
            for i in range(3):
                for j in range(3):
                    self.planes.append(
                        self.makePlane(xmin=x, xmax=x, ymin=j, ymax=j + 1, zmin=i, zmax=i + 1, colour=colours[counter])
                    )
                    counter += 1

        # Faces perpendicular to y-axis (Blue/Green)
        for y in [0, 3]:
            for i in range(3):
                for j in range(3):
                    self.planes.append(
                        self.makePlane(xmin=j, xmax=j + 1, ymin=y, ymax=y, zmin=i, zmax=i + 1, colour=colours[counter])
                    )
                    counter += 1

        self.plottingPlanes = [p["corners"] for p in self.planes]
        self.plottingColours = [p["colour"] for p in self.planes]

        poly = Poly3DCollection(self.plottingPlanes, facecolors=self.plottingColours, edgecolors="black", linewidths=7)
        self.ax.add_collection3d(poly)

        self.ax.set_xlim(0, 3)
        self.ax.set_ylim(0, 3)
        self.ax.set_zlim(0, 3)
        plt.axis("off")

        return self.planes

    def getPlanesToRotate(self, move: str) -> list[int]:
        """Get the indices of planes to rotate for a given move.

        Args:
            move (str): The move to get planes for (e.g., "R", "U'", etc.).

        Returns:
            list[int]: List of indices of planes to rotate.
        """
        centers = np.array([p["center"] for p in self.planes])
        facePos = FACE_CENTER_POSITIONS[move[0]]

        indices = [i for i, c in enumerate(centers) if abs(getDistance(c, facePos)) < 2]

        return indices

    def makeMove(self, move: str, angle: float = np.pi / 2) -> None:
        """Make a move on the cube plotter.
        Args:
            move (str): The move to make (e.g., "R", "U'", etc.).
            angle (float): The angle to rotate by (radians).
        """
        direction = -1 if len(move) == 2 else 1
        move = move[0]
        indices = self.getPlanesToRotate(move)
        axis = AXIS_MAP[move]
        faceCenter = FACE_CENTER_POSITIONS[move]
        rotatePlanes(self.planes, indices, axis, direction * angle, faceCenter)

    def updatePlot(self, planes: list[dict] = None, canvas: FigureCanvasTkAgg = None):
        """Update the 3D plot with the current plane data.

        Args:
            canvas: Optional; The canvas to draw on if using with a GUI.
        """

        if planes is None:
            planes = self.planes

        self.ax.cla()
        self.plottingPlanes = [p["corners"] for p in planes]
        self.plottingColours = [p["colour"] for p in planes]

        poly = Poly3DCollection(self.plottingPlanes, facecolors=self.plottingColours, edgecolors="black", linewidths=7)
        self.ax.add_collection3d(poly)

        self.ax.set_xlim(0, 3)
        self.ax.set_ylim(0, 3)
        self.ax.set_zlim(0, 3)
        plt.axis("off")

        if canvas is not None:
            canvas.draw()

    def animateMove(
        self, move: str, steps: int = 15, canvas: FigureCanvasTkAgg = None, interval: int = 1, cubeString: str = None
    ) -> FuncAnimation:
        """Animate a move on the cube plotter.

        Args:
            move (str): The move to animate (e.g., "W", "R'", etc.).
            steps (int): Number of animation steps.
            canvas (FigureCanvasTkAgg): The canvas to draw on if using with a GUI.
            interval (int): Time between frames in milliseconds.
        """
        indices = self.getPlanesToRotate(move)

        if len(move) == 2:
            direction = -1
        else:
            direction = 1

        move = move[0]

        if cubeString is not None:
            colours = ["" for _ in range(54)]

            self.makeMove(move, angle=direction * np.pi / 2)
            for p in self.planes:
                colours[CENTER_ORDERINGS[tuple(map(lambda x: round(x, 2), p["center"]))]] = p["colour"]

            colourString = "".join([c for c in colours])

            self.makeMove(move, angle=-direction * np.pi / 2)  # revert the move

            if colourString != cubeString:
                direction *= -1

        axis = AXIS_MAP[move]
        faceCenter = FACE_CENTER_POSITIONS[move]
        totalAngle = direction * np.pi / 2
        angleStep = totalAngle / steps

        def update(frame):
            rotatePlanes(self.planes, indices, axis, angleStep, faceCenter)
            self.updatePlot(canvas=canvas)

        ani = FuncAnimation(self.fig, update, frames=steps - 1, interval=interval, repeat=False)
        return ani
