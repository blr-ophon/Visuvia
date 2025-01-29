"""
gui_init functio to initialize the application.
"""


import tkinter as tk
from tkinter import font

from visuvia.utils.serial_ctrl import SerialCtrl
from ..gui.serialmanager import SerialManagerGUI
from ..gui.connmanager import ConnManagerGUI


def init():
    """
    Initialize the GUI in a screen size root.
    """
    # Create root
    root = tk.Tk()
    set_default_font(root)
    create_menu_bar(root)

    # set_default_font(root, font_family="Noto Sans", font_size=10)

    root.title("MCTP GUI")
    root.config(bg="lightgrey")
    root.resizable(True, True)
    root.grid_rowconfigure(3, weight=1)
    root.grid_columnconfigure(1, weight=1)

    # Set root size to whole screen size
    screen_width = root.winfo_screenwidth()
    screen_height = root.winfo_screenheight()
    root.geometry(f"{screen_width}x{screen_height}")

    serial_ctrl = SerialCtrl()

    # GUI
    connman_gui = ConnManagerGUI(root, serial_ctrl)
    connman_gui.place_widgets()
    serialman_gui = SerialManagerGUI(root, serial_ctrl, connman_gui)
    serialman_gui.place_widgets()

    root.mainloop()


def set_default_font(root, family="fixed", size=10):
    default_font = font.nametofont("TkDefaultFont")

    default_font.configure(size=size)

    available_fonts = tk.font.families()
    if family in available_fonts:
        default_font.configure(family=family)

    # for av_font in available_fonts:
    #     print(av_font)

    root.option_add("*Font", default_font)

def create_menu_bar(root):
    menubar = tk.Menu(root)

    # Preferences menu
    preferences = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Preferences', menu=preferences)
    # preferences.add_command(label='Fonts', command=create_font_menu)
    preferences.add_command(
        label='Fonts',
        command=lambda root=root: create_font_menu(root)
    )
    preferences.add_separator()
    preferences.add_command(label='Exit', command=root.destroy)

    # Settings menu
    settings = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Settings', menu=settings)
    settings.add_command(label='Add Labels', command=None, state="disabled")

    # Help menu
    settings = tk.Menu(menubar, tearoff=0)
    menubar.add_cascade(label='Help', menu=settings)
    settings.add_command(label='Add Labels', command=None, state="disabled")

    root.config(menu=menubar)

