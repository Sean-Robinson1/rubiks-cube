import matplotlib.pyplot as plt
import numpy as np
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from mpl_toolkits.mplot3d import Axes3D
from mpl_toolkits.mplot3d.art3d import Poly3DCollection

from .constants import AXIS_MAP, CENTER_ORDERINGS, FACE_CENTER_POSITIONS
from .plotter_utils import getDistance, rotatePlanes


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
        self, xmin: float, xmax: float, ymin: float, ymax: float, zmin: float, zmax: float, colour: str, colourName: str
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

        return {"center": center, "corners": corners, "colour": colour, "colourName": colourName}

    def plotRubiks3D(self, colours: list[list[str]]) -> tuple[plt.Figure, Axes3D, list[dict]]:
        """Create plane data for a Rubik's Cube and plot them.

        Args:
            colours (list[list[str]]): A flat list (length 54) of colours.

        Returns:
            tuple[plt.Figure, Axes3D, list[dict]]: The figure, axis, and list of plane dicts.
        """
        self.planes = []
        counter = 0
        self.ax.cla()

        colourNames = ["White", "Yellow", "Red", "Orange", "Blue", "Green"]

        # Faces perpendicular to z-axis (White/Yellow)
        for z in [0, 3]:
            for i in range(3):
                for j in range(3):
                    self.planes.append(
                        self.makePlane(
                            xmin=i,
                            xmax=i + 1,
                            ymin=j,
                            ymax=j + 1,
                            zmin=z,
                            zmax=z,
                            colour=colours[counter],
                            colourName=colourNames[counter // 9],
                        )
                    )
                    counter += 1

        # Faces perpendicular to x-axis (Red/Orange)
        for x in [0, 3]:
            for i in range(3):
                for j in range(3):
                    self.planes.append(
                        self.makePlane(
                            xmin=x,
                            xmax=x,
                            ymin=j,
                            ymax=j + 1,
                            zmin=i,
                            zmax=i + 1,
                            colour=colours[counter],
                            colourName=colourNames[counter // 9],
                        )
                    )
                    counter += 1

        # Faces perpendicular to y-axis (Blue/Green)
        for y in [0, 3]:
            for i in range(3):
                for j in range(3):
                    self.planes.append(
                        self.makePlane(
                            xmin=j,
                            xmax=j + 1,
                            ymin=y,
                            ymax=y,
                            zmin=i,
                            zmax=i + 1,
                            colour=colours[counter],
                            colourName=colourNames[counter // 9],
                        )
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
                colours[CENTER_ORDERINGS[tuple(map(lambda x: round(x, 2), p["center"]))]] = p["colourName"]

            colourString = "".join([c for c in colours])

            self.makeMove(move, angle=-direction * np.pi / 2)

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
