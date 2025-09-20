import numpy as np
from mpl_toolkits.mplot3d import Axes3D

from .constants import FACE_NORMALS


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


def getRelativeFaces(ax: Axes3D) -> tuple[str, str]:
    """Gets the relative top and front vectors when moving the cube in 3D. This is
    used so that all the move buttons act relative to the front facing face.

    Args:
        ax (Axes3D): The current axis

    Returns:
        tuple[str, str]: The front and top face names.
    """

    azimRad = np.deg2rad(ax.azim)
    elevRad = np.deg2rad(ax.elev)

    view = np.array(
        [
            np.cos(elevRad) * np.sin(azimRad),  # x
            np.cos(elevRad) * np.cos(azimRad),  # y
            np.sin(elevRad),  # z
        ]
    )

    up = np.array(
        [
            -np.sin(elevRad) * np.sin(azimRad),  # x
            -np.sin(elevRad) * np.cos(azimRad),  # y
            np.cos(elevRad),  # z
        ]
    )

    # Find the front face (max dot with view vector)
    front = max(FACE_NORMALS, key=lambda f: np.dot(view, f[1]))[0][0]
    # Find the top face (max dot with up vector)
    top = max(FACE_NORMALS, key=lambda f: np.dot(up, f[1]))[0][0]

    return front, top
