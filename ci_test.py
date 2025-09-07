from cube import Cube
from threading import Thread

TIMEOUT = 90 # seconds

def run_analysis():
    cube = Cube()
    results = cube.analyseSolves(1000, displayAllTimes = False, displayStats=True)
    return results

def main():
    thread = Thread(target=run_analysis)
    thread.start()
    thread.join(TIMEOUT)
    if thread.is_alive():
        print(f"Analysis did not complete within {TIMEOUT} seconds.")
        raise TimeoutError("Analysis timed out.")

if __name__ == "__main__":
    main()