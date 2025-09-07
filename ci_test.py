from cube import Cube
from threading import Thread
import queue

TIMEOUT = 90 # seconds

def run_analysis(q: queue.Queue):
    try:
        cube = Cube()
        results = cube.analyseSolves(1000, displayAllTimes=False, displayStats=True)
        q.put(results)
    except Exception as e:
        q.put(e)

def main():
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