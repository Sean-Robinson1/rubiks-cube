import queue
from threading import Thread

from cube import Cube

TIMEOUT = 45  # seconds


def run_analysis(q: queue.Queue) -> None:
    """Runs the cube analysis in a separate thread and puts the result in the queue.

    Args:
        q (queue.Queue): The queue to put the result in.
    """
    try:
        cube = Cube()
        results = cube.analyseSolves(1000, displayAllTimes=False, displayStats=True)
        q.put(results)
    except Exception as e:
        q.put(e)


def main() -> None:
    """Main function to run the cube analysis with a timeout."""
    q = queue.Queue()
    thread = Thread(target=run_analysis, args=(q,))
    thread.start()
    thread.join(TIMEOUT)

    if thread.is_alive():
        print(f"Analysis did not complete within {TIMEOUT} seconds.")
        raise TimeoutError("Analysis timed out")

    try:
        result = q.get_nowait()
        if isinstance(result, Exception):
            print("Error during analysis:", result)
            raise result

    except queue.Empty:
        raise RuntimeError("Analysis thread finished without returning a result")


if __name__ == "__main__":
    main()
