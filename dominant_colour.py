import cv2
import numpy as np

def getDominantColours(image:np.ndarray, numClusters: int=2) -> list[tuple]:
    """
    Finds the dominant colours in an image
    """
    # Reshape the image data
    height, width, channels = image.shape
    data = np.reshape(image, (height * width, channels)).astype(np.float32)

    # Define the termination criteria
    criteria = (cv2.TERM_CRITERIA_EPS + cv2.TERM_CRITERIA_MAX_ITER, 10, 1.0)

    # Apply k-means clustering
    flags = cv2.KMEANS_RANDOM_CENTERS
    compactness, labels, centers = cv2.kmeans(data, numClusters, None, criteria, 10, flags)

    # Convert the dominant colors to RGB format
    dominantColours = [(c[2], c[1], c[0]) for c in centers]

    return dominantColours


if __name__ == "__main__":
    # Define the colour of the image
    colour = (255, 255, 0)  # yellow colour

    # Create a 3-channel array of the desired colour
    colourArray = np.zeros((400, 400, 3), dtype=np.uint8)
    colourArray[:] = colour

    # Create a new OpenCV image using the color array
    image = cv2.cvtColor(colourArray, cv2.COLOR_RGB2BGR)

    x, y, w, h = 100, 100, 300, 300
    colour = (0, 0, 0) # black color

    # Draw the rectangle on the image
    cv2.rectangle(image, (x, y), (x+w, y+h), colour, -1)

    dominantColours = getDominantColours(image)
    print(dominantColours)

    dominantColour = dominantColours[0]

    print(dominantColour)

    colourArray = np.zeros((400, 400, 3), dtype=np.uint8)
    colourArray[:] = dominantColour

    # Create a new OpenCV image using the color array
    image2 = cv2.cvtColor(colourArray, cv2.COLOR_RGB2BGR)

    # Display the image
    cv2.imshow('Yellow Square', image)
    cv2.imshow('Dominant Colour', image2)
    cv2.waitKey(0)
    cv2.destroyAllWindows()