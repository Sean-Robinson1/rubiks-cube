import logging

import cv2
import numpy as np


def getDominantColours(image: np.ndarray, numClusters: int = 2) -> list[tuple]:
    """
    Finds the dominant colours in an image

    Args:
        image (np.ndarray): The image to find the dominant colours in.
        numClusters (int, optional): The number of dominant colours to find. Defaults to 2.

    Returns:
        list[tuple]: A list of the dominant colours in BGR format.
    """

    height, width, channels = image.shape
    data = np.reshape(image, (height * width, channels)).astype(np.float32)

    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

    flags = cv2.KMEANS_RANDOM_CENTERS
    _, _, centers = cv2.kmeans(data, numClusters, None, criteria, 10, flags)

    dominantColours = [(c[2], c[1], c[0]) for c in centers]

    logging.info(f"Found dominant colours: {dominantColours}")

    return dominantColours
