from .constants import STRING_ROTATION_MAPPINGS


# these functions perform operations on the masks not the cube
# this is because it is more efficient to manipulate the mask directly than the cube
# especially during the recursive BFS
def rotate(mask: str, rotation: str) -> str:
    """Rotates a mask given a specific rotation.

    Args:
        mask (str): The mask to rotate.
        rotation (str): The rotation to perform.

    Returns:
        str: The rotated mask.
    """
    output = ""
    mapping = STRING_ROTATION_MAPPINGS[rotation]
    for i in range(54):
        output += mask[mapping[i]]
    return output


def checkMask(mask: str, state: str) -> bool:
    """Checks if a mask and a state match.

    Args:
        mask (str): The mask to check.
        state (str): The state to check against.

    Returns:
        bool: True if the mask matches the state, False otherwise.
    """
    for i in range(len(mask)):
        if mask[i] != "." and mask[i] != state[i]:
            return False
    return True


def optimiseMoves(moves: list[str]) -> list[str]:
    """
    Looks through a list of moves and applies general rules to reduce the
    total number of rotations while maintaining the same output. i.e. running
    this function will result in a shorter list of moves that will perform
    the same transformation on the cube.

    Args:
        moves (list[str]): The list of moves to optimise.

    Returns:
        list[str]: The optimised list of moves.
    """
    ## checking if there is a repeated section of 4
    newList = []
    i = 0
    while i <= len(moves) - 4:
        if moves[i] == moves[i + 1] == moves[i + 2] == moves[i + 3]:
            i += 4
        else:
            newList.append(moves[i])
            i += 1

    newList += moves[i:]

    ## replacing repeated sections of length 3
    moves = newList.copy()
    newList = []
    i = 0
    while i <= len(moves) - 3:
        if moves[i] == moves[i + 1] == moves[i + 2]:
            if len(moves[i]) == 1:
                newList.append(moves[i] + "i")
            else:
                newList.append(moves[i][0])
            i += 3

        else:
            newList.append(moves[i])
            i += 1

    newList += moves[i:]

    ## removing all occurences of a move followed by its inverse

    moves = newList.copy()
    newList = []
    i = 0
    skippedLast = False
    while i < len(moves) - 1:
        if moves[i][0] == moves[i + 1][0] and moves[i] != moves[i + 1]:
            i += 2
            skippedLast = False
        else:
            newList.append(moves[i])
            i += 1
            skippedLast = True

    if skippedLast:
        newList.append(moves[-1])

    return newList


def printAnalysis(analysis: dict) -> None:
    """Prints the analysis of multiple solves to the console.

    Args:
        analysis (dict): The analysis dictionary containing the statistics.
    """

    print("\n-----------------------------")
    print(f"Average Solve Time: {analysis['avg_time']}")
    print(f"Avg number of Rotations: {round(analysis['avg_moves'], 5)}")
    print(f"Avg number of optimised rotations: {round(analysis['avg_moves_optimised'], 5)}")
    print(f"Avg number of rotations saved:  {round(analysis['avg_moves_saved'],2)}")

    print("-----------------------------")

    print(f"Avg Cross Time: {analysis['avg_cross_time']}")
    print(f"Avg Corners Time: {analysis['avg_corners_time']}")
    print(f"Avg Middles Time: {analysis['avg_middles_time']}")
    print(f"Avg Yellow Cross Time: {analysis['avg_yellow_cross_time']}")
    print(f"Avg Yellow Edges Time: {analysis['avg_yellow_edges_time']}")
    print(f"Avg Final Time: {analysis['avg_final_time']}")

    print("-----------------------------")

    print(f"Max Cross Time: {analysis['max_cross_time']}")
    print(f"Max Corners Time: {analysis['max_corners_time']}")
    print(f"Max Middles Time: {analysis['max_middles_time']}")
    print(f"Max Yellow Cross Time: {analysis['max_yellow_cross_time']}")
    print(f"Max Yellow Edges Time: {analysis['max_yellow_edges_time']}")
    print(f"Max Final Time: {analysis['max_final_time']}")
    print("-----------------------------")
