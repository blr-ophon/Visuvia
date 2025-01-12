# Third party imports
import tkinter as tk
from tkinter import messagebox
# Local imports
from visuvia.utils.serial_ctrl import SerialCtrlError


__all__ = ["SerialManagerGUI"]


class SerialManagerGUI():
    """
    GUI to open/close ports and start/stop MCTP connection.
    Has methods to create, manage and place widgets on the window.

    Attributes:
        window (tk.Tk): the tk window.
        connman_gui (ConnManagerGUI): Connection Manager.
        serial_ctrl (SerialCtrl): Serial port manager.
        frame (tk.LabelFrame): Menu frame.
        btn_refresh (tk.Button): Refresh button.
        btn_connect (tk.Button): Connect button.
        drop_ports (tk.OptionMenu): Ports drop menu.
        clicked_port (tk.StringVar): Selected port.
        drop_bd (tk.OptionMenu): Baud rate drop menu.
        clicked_bd (tk.StringVar): Selected baud rate.

    Public Methods:
        place_widgets: Place widgets on window.

    Internal Methods:
        _port_menu: Create drop menu with available ports.
        _baudrate_menu: Create drop menu with baud rates.
        _ports_refresh: Refresh ports menu.
        _connect: Start MCTP connection.
        _disconnect: Stop MCTP connection.

    Private Methods:
        __connect_ctrl: Checks if 'Connect' button can be enabled.
    """
    def __init__(self, window, serial_ctrl, connman_gui):
        self.window = window
        self.connman_gui = connman_gui
        self.serial_ctrl = serial_ctrl

        # Frame
        self.frame = tk.LabelFrame(master=window, text="Serial Manager",
                                   padx=5, pady=5, bg="lightgrey")
        # Static widgets
        lbl_com = tk.Label(self.frame, text="Available Port(s): ",
                           bg="lightgrey", width=15, anchor="w")
        lbl_com.grid(column=1, row=2)
        lbl_bd = tk.Label(self.frame, text="Baud rate: ",
                          bg="lightgrey", width=15, anchor="w")
        lbl_bd.grid(column=1, row=3)

        # Dynamic widgets
        self.btn_refresh = tk.Button(master=self.frame, text="Refresh",
                                     width=10, command=self._ports_refresh)
        self.btn_connect = tk.Button(master=self.frame, text="Connect",
                                     width=10, state="disabled",
                                     command=self._connect)
        self.clicked_port = tk.StringVar()
        self.drop_ports = None
        self.clicked_bd = tk.StringVar()
        self.drop_bd = None

        # Menus
        self._port_menu()
        self._baudrate_menu()
        self.__connect_ctrl(None)

    def _port_menu(self):
        """
        Create a drop menu widget to select Comm port
        """
        # Scan COM ports
        coms = self.serial_ctrl.get_port_list()
        coms.insert(0, "-")

        # StringVar is needed to operate with OptionMenu widget
        self.clicked_port.set(coms[-1])

        self.drop_ports = tk.OptionMenu(
            self.frame,     # master
            self.clicked_port,
            *coms,
            command=self.__connect_ctrl,
        )
        self.drop_ports.config(width=10)

    def _baudrate_menu(self):
        """
        Create a drop menu widget to select Baud Rate.
        """
        bds = ["-", "300", "600", "1200", "2400", "4800",
               "9600", "14400", "19200", "28800", "38400",
               "56000", "57600", "115200", "128000", "256000"]

        self.clicked_bd.set(bds[13])
        self.drop_bd = tk.OptionMenu(
            self.frame,
            self.clicked_bd,
            *bds,
            command=self.__connect_ctrl,
        )
        self.drop_bd.config(width=10)

    def __connect_ctrl(self, widget):
        """
        Enable 'Connect' button when a value from the 2 drop menus is selected.
        Callback for both port and baud rate menus.
        """
        if "-" in (self.clicked_port.get(), self.clicked_bd.get()):
            self.btn_connect["state"] = "disable"
        else:
            self.btn_connect["state"] = "normal"

    def place_widgets(self):
        """
        Publish widgets grid on Communication frame.
        """
        self.frame.grid(row=0, column=0, padx=5, pady=5,
                        sticky="nsew")

        self.drop_ports.grid(column=2, row=2)
        self.drop_bd.grid(column=2, row=3)
        self.btn_refresh.grid(column=3, row=2)
        self.btn_connect.grid(column=3, row=3)

    def _ports_refresh(self):
        """
        Rescan serial ports to display on drop menu.
        """
        self.drop_ports.destroy()
        self._port_menu()
        self.drop_ports.grid(column=2, row=2)
        self.__connect_ctrl(None)

    def _connect(self):
        """
        Try to open serial port and start establish MCTP connection.
        Callback for 'Connect' button.
        """
        if self.btn_connect["text"] in "Connect":
            # Try opening port
            port_name = self.clicked_port.get()
            baudrate = self.clicked_bd.get()
            try:
                self.serial_ctrl.set_serial(port_name=port_name,
                                            baudrate=baudrate, timeout=2)
                # Update widgets.
                self.btn_connect["text"] = "Disconnect"
                self.btn_refresh["state"] = "disable"
                self.drop_bd["state"] = "disable"
                self.drop_ports["state"] = "disable"
            except SerialCtrlError as exc:
                error_msg = f"Failure to establish serial connection using\
                            {self.clicked_port.get()}"
                messagebox.showerror("showerror", error_msg)
                print(f"Connect error: {exc}")
                return

            # Start connection
            self.connman_gui.start_comm()
        else:
            self._disconnect()

    def _disconnect(self):
        """
        Stop MCTP connection and close serial port.
        Callback for 'Connect' button.
        """
        self.connman_gui.display_disable()
        self.serial_ctrl.close_serial()

        self.btn_connect["text"] = "Connect"
        self.btn_refresh["state"] = "normal"
        self.drop_bd["state"] = "normal"
        self.drop_ports["state"] = "normal"


