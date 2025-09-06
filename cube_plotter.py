import matplotlib.pyplot as plt
from mpl_toolkits.mplot3d import Axes3D
import numpy as np

COLOURS = ['White','Yellow','Red','Orange','Blue','Green']
colours = []
for colour in COLOURS:
    colours += [colour] * 9

def plotRubiks3D(colours:list[list[str]], ax: Axes3D | None = None) -> Axes3D:
    """
    Plots an interactive 3D representation of a Rubik's Cube.
    """
    plt.ion()
    counter = 0
    if not ax:
        fig, ax = plt.subplots(subplot_kw={"projection": "3d"})
    else:
        while len(ax.artists) > 0:
            ax.artists[0].remove()

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
    plt.pause(0.1)
    return ax

def renderAll() -> None:
    plt.show()

def change_I_mode() -> None:
    if plt.isinteractive():
        plt.ioff()
    else:
        plt.ion()
