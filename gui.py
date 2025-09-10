from cube_plotter import plotRubiks3D, createFig
from cube_scanner import getCubeString
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from cube import Cube
import tkinter as tk
import numpy as np

# Face normals: (name, [x, y, z])
faceNormals = [
    ("White",  [0, 0, -1]),   
    ("Yellow", [0, 0, 1]),  
    ("Blue",   [1, 0, 0]),  
    ("Green",  [-1, 0, 0]), 
    ("Red",    [0, -1, 0]), 
    ("Orange", [0, 1, 0]), 
]

def getRelativeFaces(ax):
    # Convert azim/elev to a viewing vector
    azimRad = np.deg2rad(ax.azim)
    elevRad = np.deg2rad(ax.elev)
    # Spherical to Cartesian
    view = np.array([
        np.cos(elevRad) * np.sin(azimRad),  # x
        np.cos(elevRad) * np.cos(azimRad),  # y
        np.sin(elevRad)                      # z
    ])

    up = np.array([
        -np.sin(elevRad) * np.sin(azimRad),  # x
        -np.sin(elevRad) * np.cos(azimRad),  # y
        np.cos(elevRad)                       # z
    ])

    # Find the front face (max dot with view vector)
    front = max(faceNormals, key=lambda f: np.dot(view, f[1]))[0][0]
    # Find the top face (max dot with up vector)
    top = max(faceNormals, key=lambda f: np.dot(up, f[1]))[0][0]

    return front, top

class GUI:
    def __init__(self, cube: Cube):
        self.cube = cube
        self.fig, self.ax = createFig()
        self.canvas = None

    def plot3D(self) -> None:
        """
        Plots the cube in 3D.
        """
        self.fig, self.ax = plotRubiks3D(self.cube.getPlottingList(),self.ax, self.fig)
        self.canvas.draw()

    def createTkWindow(self) -> None:
        self.tk = tk.Tk()
        self.tk.title("Rubik's Cube")

        w, h = self.tk.winfo_screenwidth(), self.tk.winfo_screenheight()
        self.tk.geometry(f"{w//2}x{h//2}")

        # Create main horizontal container using pack
        main_container = tk.Frame(self.tk)
        main_container.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)

        # Calculate dimensions for 60% canvas, 40% buttons split
        canvas_width = int((w//2) * 0.6)  # 60% of window width for canvas
        button_width = int((w//2) * 0.35)  # 35% for buttons, 5% for padding
        
        # Canvas frame on the left - fixed size
        canvas_frame = tk.Frame(main_container, bg='lightgray', width=canvas_width)
        canvas_frame.pack(side=tk.LEFT, fill=tk.Y)
        canvas_frame.pack_propagate(False)  # Maintain fixed width
        
        # Create matplotlib canvas
        self.canvas = FigureCanvasTkAgg(self.fig, master=canvas_frame)
        self.canvas.get_tk_widget().pack(fill=tk.BOTH, expand=False)
        
        self.plot3D()
        self.ax.view_init(elev=210, azim=120)

        # Button frame on the right - fixed width
        button_frame = tk.Frame(main_container, bg='white', width=button_width)
        button_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=(20, 0))
        button_frame.pack_propagate(False)  # Prevent frame from shrinking

        # Title for button section
        title_label = tk.Label(button_frame, text="Cube Rotations", 
                            font=('Arial', 14, 'bold'), bg='white')
        title_label.pack(pady=(10, 20))

        button_names = ["R", "L", "U", "D", "F", "B", "R'", "L'", "U'", "D'", "F'", "B'"]
        button_funcs = [self.cube.rotateR, self.cube.rotateL, self.cube.rotateU, self.cube.rotateD, self.cube.rotateF, self.cube.rotateB, lambda: self.cube.rotateR(-1), lambda: self.cube.rotateL(-1), lambda: self.cube.rotateU(-1),
                            lambda: self.cube.rotateD(-1), lambda: self.cube.rotateF(-1), lambda: self.cube.rotateB(-1)]

         # Create button container with two columns
        button_container = tk.Frame(button_frame, bg='white')
        button_container.pack(fill=tk.BOTH, expand=True, padx=10)
        
        # Configure two columns in button container
        button_container.grid_columnconfigure(0, weight=1)
        button_container.grid_columnconfigure(1, weight=1)

        # Create buttons with better spacing
        for i, (name, func) in enumerate(zip(button_names, button_funcs)):
            btn = tk.Button(
                button_container,
                text=name,
                font=('Arial', 10, 'bold'),
                width=12,
                height=2,
                bg='lightblue',
                activebackground='darkblue',
                activeforeground='white',
                command=lambda name=name: [self.cube.calculateFaces(*getRelativeFaces(self.ax)), self.cube.executeSequenceRelative(name), self.plot3D()]  # Update the canvas after rotation
            )
            btn.grid(row=i%6, column=i//6, padx=5, pady=5, sticky='nsew')

        # Add some additional controls at the bottom
        control_frame = tk.Frame(button_frame, bg='white')
        control_frame.pack(side=tk.BOTTOM, fill=tk.X, padx=10, pady=20)

        control_frame.grid_columnconfigure(0, weight=1)
        control_frame.grid_columnconfigure(1, weight=1)
        
        reset_btn = tk.Button(
            control_frame,
            text="Reset View",
            font=('Arial', 10),
            bg='lightcoral',
            activebackground='darkred',
            activeforeground='white',
            command=lambda: [self.ax.view_init(elev=210, azim=120), self.plot3D()]
        )
        reset_btn.grid(row=0, column=0, sticky='ew', pady=5, padx=(0,5))

        scramble_btn = tk.Button(
            control_frame,
            text="Scramble",
            font=('Arial', 10),
            bg='lightgreen',
            activebackground='darkgreen',
            activeforeground='white',
            command=lambda: [self.cube.randomiseCube(), self.plot3D()]
        )
        scramble_btn.grid(row=0, column=1, sticky='ew', pady=5, padx=(5,0))

        scan_btn = tk.Button(
            control_frame,
            text="Scan Cube",
            font=('Arial', 13),
            bg='lightyellow',
            activebackground='goldenrod',
            activeforeground='white',
            command=lambda: [self.cube.initialiseFaces(getCubeString()), self.plot3D()]
        )
        scan_btn.grid(row=1, column=0, columnspan=2, sticky='ew', pady=5)

        solve_btn = tk.Button(
            control_frame,
            text="Solve",
            font=('Arial', 13),
            bg='lightgreen',
            activebackground='darkgreen',
            activeforeground='white',
            command=lambda: [self.cube.solve(), self.plot3D()]
        )
        solve_btn.grid(row=2, column=0, columnspan=2, sticky='ew', pady=5)