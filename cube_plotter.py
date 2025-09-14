import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

COLOURS = ['White','Yellow','Red','Orange','Blue','Green']
colours = []
for colour in COLOURS:
    colours += [colour] * 9

def createFig() -> tuple[plt.Figure, Axes3D]:
    """Creates a 3D fig and ax.
    
    Returns:
        tuple[plt.Figure, Axes3D]: The figure and 3D axis.
    """
    fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    return fig, ax

def plotRubiks3D(colours: list[list[str]], ax: Axes3D, fig: plt.Figure) -> tuple[plt.Figure, Axes3D]:
    """Plots an interactive 3D representation of a Rubik's Cube.
    
    Args:
        colours (list[list[str]]): A list of lists containing the colours of each face of the cube.
        ax (Axes3D): The 3D axis to plot on.
        fig (plt.Figure): The figure to plot on.

    Returns:
        tuple[plt.Figure, Axes3D]: The figure and 3D axis.
    """

    counter = 0

    # clears the axis for re-plotting
    ax.cla()

    # plots planes perpendicular to the z-axis (White/Yellow)
    for z in [0,3]:
        for i in range(3):
            for ii in range(3):
                X = np.arange(0+i, 1+i, 0.99)
                Y = np.arange(0+ii, 1+ii, 0.99)

                X, Y = np.meshgrid(X, Y)
                Z = X * 0 + z

                ax.plot_surface(X, Y, Z, linewidth=0, color=colours[counter])
                counter += 1

    # plots planes perpendicular to the x-axis (Blue/Green)
    for x in [0,3]:
        for i in range(3):
            for ii in range(3):
                Z = np.arange(0+i, 1+i, 0.99)
                Y = np.arange(0+ii, 1+ii, 0.99)

                Z, Y = np.meshgrid(Z, Y)
                X = Z * 0 + x

                ax.plot_surface(X, Y, Z, linewidth=0, color=colours[counter])
                counter += 1

    # plots planes perpendicular to the y-axis (Red/Orange)
    for y in [0,3]:
        for i in range(3):
            for ii in range(3):
                Z = np.arange(0+i, 1+i, 0.99)
                X = np.arange(0+ii, 1+ii, 0.99)

                Z, X = np.meshgrid(Z,X)
                Y = X * 0 + y

                ax.plot_surface(X, Y, Z, linewidth=0, color=colours[counter])
                counter += 1

    plt.axis('off')
    return fig, ax
