import logging
import tkinter as tk

from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg

from .colour_calibration import CubeCalibrator
from .cube import Cube
from .cube_plotter import CubePlotter
from .cube_scanner import CubeScanner
from .plotter_utils import getRelativeFaces


class GUI:
    def __init__(self, cube: Cube) -> None:
        """Initialises the GUI with a Cube object."""
        logging.info("Initialising GUI")
        self.cube = cube
        self.canvas = None
        self.scanner = None
        self.tk = tk.Tk()
        self.tk.title("Rubik's Cube")
        self.tk.protocol("WM_DELETE_WINDOW", self.onClose)
        self.w, self.h = self.tk.winfo_screenwidth(), self.tk.winfo_screenheight()
        self.tk.geometry(f"{self.w}x{self.h}")
        self.mainloopStarted = False
        self.calibratedColours = None
        self.showAnimations = True
        self.plotter = CubePlotter()
        self.ani = None

    def onClose(self) -> None:
        """Called when the main window is closed: stop scanner, release camera and exit."""
        if getattr(self, "scanner", None):
            self.scanner.stop()

        self.tk.quit()
        self.tk.destroy()

    def plot3D(self) -> None:
        """Plots the cube in 3D, using a matplotlib window for the cube."""
        plottingList = self.cube.getPlottingList()

        if self.calibratedColours is not None:
            plottingList = [self.calibratedColours[col] / 256 for col in plottingList]

        logging.info(f"Plotting list: {plottingList}")

        self.plotter.plotRubiks3D(plottingList)
        self.canvas.draw()

    def solveCube(self) -> None:
        """Solves the cube, and creates a TopLevel window with the moves to solve the cube."""
        logging.info("Solving cube")

        self.cube.solve()
        moves = " ".join(self.cube.optimisedMoves)

        top = tk.Toplevel(self.tk)
        top.title("Solution")
        top.transient(self.tk)
        top.resizable(False, False)
        top.configure(bg="#f8f9fa")

        w, h = 600, 380
        try:
            x = self.tk.winfo_rootx() + (self.tk.winfo_width() - w) // 2
            y = self.tk.winfo_rooty() + (self.tk.winfo_height() - h) // 2
        except Exception:
            x = y = 100
        top.geometry(f"{w}x{h}+{x}+{y}")

        frame = tk.Frame(top, bg="#f8f9fa", padx=14, pady=12)
        frame.pack(fill=tk.BOTH, expand=True)

        header = tk.Frame(frame, bg="#f8f9fa")
        header.pack(fill=tk.X, pady=(0, 8))
        tk.Label(header, text="Cube Solution", bg="#f8f9fa", fg="#111", font=("Arial", 20, "bold")).pack(side=tk.LEFT)
        tk.Label(
            header,
            text=f"{len(self.cube.optimisedMoves)} moves",
            bg="#f8f9fa",
            fg="#666",
            font=("Arial", 16),
        ).pack(side=tk.RIGHT)

        btn_frame = tk.Frame(frame, bg="#f8f9fa", height=70)
        btn_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(10, 0))
        btn_frame.pack_propagate(False)

        text_frame = tk.Frame(frame, bg="#ffffff", relief=tk.FLAT, bd=1)
        text_frame.pack(fill=tk.BOTH, expand=True)
        scrollbar = tk.Scrollbar(text_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        text = tk.Text(
            text_frame,
            wrap="word",
            yscrollcommand=scrollbar.set,
            font=("Consolas", 15),
            bg="white",
            fg="#222",
            relief=tk.FLAT,
            bd=0,
            padx=10,
            pady=8,
        )
        text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=text.yview)

        text.insert("1.0", moves if moves else "(no moves)")
        text.config(state="disabled")

        def copy_moves():
            try:
                self.tk.clipboard_clear()
                self.tk.clipboard_append(moves)
            except Exception:
                logging.error("Failed to copy moves to clipboard")
                pass

        def close():
            top.grab_release()
            top.destroy()

        center_row = tk.Frame(btn_frame, bg="#f8f9fa")
        center_row.pack(expand=True)

        copy_btn = tk.Button(
            center_row,
            text="Copy",
            command=copy_moves,
            width=16,
            height=2,
            bg="#2B7CFF",
            fg="white",
            activebackground="#1A5FD6",
            font=("Arial", 16, "bold"),
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
        )
        copy_btn.pack(side=tk.LEFT, padx=12)

        close_btn = tk.Button(
            center_row,
            text="Close",
            command=close,
            width=16,
            height=2,
            bg="#E9ECEF",
            fg="#222",
            activebackground="#DDE3EA",
            font=("Arial", 16, "bold"),
            bd=0,
            relief=tk.FLAT,
            cursor="hand2",
        )
        close_btn.pack(side=tk.LEFT, padx=12)

        top.grab_set()
        top.focus_force()

    def startScan(self) -> None:
        """Starts scanning the cube from the webcam and embeds it in the tkinter window."""
        logging.info("Starting cube scan")

        for widget in self.tk.winfo_children():
            widget.destroy()

        self.video_label = tk.Label(self.tk)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        self.scanner = CubeScanner(self.video_label, self.calibratedColours)
        btn_row = tk.Frame(self.tk)
        btn_row.pack(side=tk.BOTTOM, pady=10)

        def cancel_scan():
            logging.info("Cancelling cube scan")
            self.scanner.stop()
            self.plotter = CubePlotter()
            self.createTkWindow()

        def end_scan():
            logging.info("Ending cube scan")
            self.scanner.stop()
            self.plotter = CubePlotter()
            self.cube.initialiseFaces(self.scanner.getCubeString())
            self.createTkWindow()

        cancel_btn = tk.Button(btn_row, text="Cancel", font=("Arial", 20), bg="lightcoral", command=cancel_scan)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        end_btn = tk.Button(btn_row, text="End Scan", font=("Arial", 20), bg="lightgreen", command=end_scan)
        end_btn.pack(side=tk.LEFT, padx=5)

    def startCalibration(self) -> None:
        """Start a colour calibration UI embedded in the Tk window."""
        logging.info("Starting colour calibration")

        for widget in self.tk.winfo_children():
            widget.destroy()

        self.video_label = tk.Label(self.tk)
        self.video_label.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # CubeCalibrator will update the label with camera frames and collect averages
        self.calibrator = CubeCalibrator(self.video_label)

        btn_row = tk.Frame(self.tk)
        btn_row.pack(side=tk.BOTTOM, pady=10)

        def cancel_cal():
            logging.info("Cancelling colour calibration")
            self.calibrator.stop()
            self.plotter = CubePlotter()
            self.createTkWindow()

        def save_cal():
            logging.info("Saving colour calibration")
            self.calibrator.stop()
            self.plotter = CubePlotter()
            self.calibratedColours = self.calibrator.getAverages()
            self.createTkWindow()

        cancel_btn = tk.Button(btn_row, text="Cancel", font=("Arial", 20), bg="lightcoral", command=cancel_cal)
        cancel_btn.pack(side=tk.LEFT, padx=5)

        save_btn = tk.Button(btn_row, text="Save Calibration", font=("Arial", 20), bg="lightgreen", command=save_cal)
        save_btn.pack(side=tk.LEFT, padx=5)

    def rotateCube(self, move: str) -> None:
        """Rotate the cube view in 3D.

        Args:
            move (str): The move to perform (e.g., "W", "R'", etc.).
        """
        logging.info(f"Rotating cube with move: {move}")

        self.cube.executeSequenceRelative(move)
        if self.showAnimations:
            # storing animation as variable to prevent garbage collection
            self.ani = self.plotter.animateMove(
                self.cube.getMoveRelative(move), canvas=self.canvas, cubeString="".join(self.cube.getPlottingList())
            )
            self.canvas.draw()
        else:
            self.plot3D()

    def createTkWindow(self) -> None:
        """Initialises the tk window, as well as all frames, buttons and the cube display."""
        logging.info("Creating main Tkinter window")

        for widget in self.tk.winfo_children():
            widget.destroy()

        main_container = tk.Frame(self.tk)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        canvas_width = int((self.w) * 0.6)
        button_width = int((self.w) * 0.35)

        canvas_frame = tk.Frame(main_container, bg="lightgray", width=canvas_width)
        canvas_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        canvas_frame.pack_propagate(False)

        self.canvas = FigureCanvasTkAgg(self.plotter.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)

        self.plot3D()
        self.plotter.ax.view_init(elev=210, azim=120)

        button_frame = tk.Frame(main_container, bg="white", width=button_width)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        button_frame.pack_propagate(False)

        title_label = tk.Label(button_frame, text="Cube Rotations", font=("Arial", 25, "bold"), bg="white")
        title_label.pack(pady=5)

        button_names = ["R", "L", "U", "D", "F", "B", "R'", "L'", "U'", "D'", "F'", "B'"]

        button_container = tk.Frame(button_frame, bg="white")
        button_container.pack(fill=tk.BOTH, expand=True, padx=10)

        button_container.grid_columnconfigure(0, weight=1)
        button_container.grid_columnconfigure(1, weight=1)

        for i, name in enumerate(button_names):
            btn = tk.Button(
                button_container,
                text=name,
                font=("Arial", 27, "bold"),
                width=12,
                height=1,
                bg="lightblue",
                activebackground="darkblue",
                activeforeground="white",
                command=lambda name=name: [
                    self.cube.calculateFaces(*getRelativeFaces(self.plotter.ax)),
                    self.rotateCube(name),
                ],
            )
            btn.grid(row=i % 6, column=i // 6, padx=5, pady=5, sticky="nsew")

        control_frame = tk.Frame(button_frame, bg="white")
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=5)

        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)

        reset_btn = tk.Button(
            control_frame,
            text="Reset View",
            font=("Arial", 18, "bold"),
            bg="lightcoral",
            activebackground="darkred",
            activeforeground="white",
            command=lambda: [self.plotter.ax.view_init(elev=210, azim=120), self.plot3D()],
        )
        reset_btn.grid(row=0, column=0, sticky="ew", pady=5, padx=(0, 5))

        scramble_btn = tk.Button(
            control_frame,
            text="Scramble",
            font=("Arial", 18, "bold"),
            bg="lightgreen",
            activebackground="darkgreen",
            activeforeground="white",
            command=lambda: [self.cube.randomise(), self.plot3D()],
        )
        scramble_btn.grid(row=0, column=1, sticky="ew", pady=5, padx=(5, 0))

        calibrate_btn = tk.Button(
            control_frame,
            text="Calibrate Colours",
            font=("Arial", 24, "bold"),
            bg="lightblue",
            activebackground="deepskyblue",
            activeforeground="white",
            command=lambda: [self.startCalibration(), self.plot3D()],
        )
        calibrate_btn.grid(row=1, column=0, columnspan=2, sticky="ew", pady=5)

        scan_btn = tk.Button(
            control_frame,
            text="Scan Cube",
            font=("Arial", 24, "bold"),
            bg="lightyellow",
            activebackground="goldenrod",
            activeforeground="white",
            command=lambda: [self.startScan(), self.plot3D()],
        )
        scan_btn.grid(row=2, column=0, columnspan=2, sticky="ew", pady=5)

        solve_btn = tk.Button(
            control_frame,
            text="Solve",
            font=("Arial", 24, "bold"),
            bg="lightgreen",
            activebackground="darkgreen",
            activeforeground="white",
            command=lambda: [self.solveCube(), self.plot3D()],
        )
        solve_btn.grid(row=3, column=0, columnspan=2, sticky="ew", pady=5)

        def toggle_animations():
            self.showAnimations = not self.showAnimations
            anim_btn.config(text=f"Animations: {'On' if self.showAnimations else 'Off'}")

        anim_btn = tk.Button(
            control_frame,
            text="Animations: On",
            font=("Arial", 18, "bold"),
            bg="lightblue",
            activebackground="deepskyblue",
            activeforeground="white",
            command=toggle_animations,
        )
        anim_btn.grid(row=4, column=0, columnspan=2, sticky="ew", pady=5)

        if not self.mainloopStarted:
            logging.info("Starting Tkinter main loop")
            self.mainloopStarted = True
            self.tk.mainloop()
