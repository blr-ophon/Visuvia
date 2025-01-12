"""
gui_init functio to initialize the application.
"""


import tkinter as tk

from visuvia.utils.serial_ctrl import SerialCtrl
from ..gui.serialmanager import SerialManagerGUI
from ..gui.connmanager import ConnManagerGUI


def init():
    """
    Initialize the GUI in a screen size window.
    """
    # Create window
    window = tk.Tk()
    window.title("MCTP GUI")
    window.config(bg="lightgrey")
    window.resizable(True, True)
    window.grid_rowconfigure(3, weight=1)
    window.grid_columnconfigure(1, weight=1)
    # Set window size to whole screen size
    screen_width = window.winfo_screenwidth()
    screen_height = window.winfo_screenheight()
    window.geometry(f"{screen_width}x{screen_height}")

    serial_ctrl = SerialCtrl()

    # GUI
    connman_gui = ConnManagerGUI(window, serial_ctrl)
    connman_gui.place_widgets()
    serialman_gui = SerialManagerGUI(window, serial_ctrl, connman_gui)
    serialman_gui.place_widgets()

    window.mainloop()
