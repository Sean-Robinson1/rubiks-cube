from cube import Cube
from gui import GUI


def main() -> None:
    cube = Cube()
    gui = GUI(cube)
    gui.createTkWindow()


if __name__ == "__main__":
    main()
