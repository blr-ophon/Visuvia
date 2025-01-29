"""
This module provides the SerialManagerGUI and ConnManagerGUI classes,
for displaying and managing associated GUI menus.

The SerialManagerGUI manages the Serial Manager menu, which provides a GUI
to establish serial connection through a port.

The ConnManagerGUI manages the Connection Manager menu, which provides a
GUI to start/stop data transfer, add/append charts, save data and display
connection status.

Dependencies:
- tkinter
"""
# TODO: Use tk frame or frm instead of frame to avoid confusion with mctp frames


# Standard library imports
from queue import Queue
# Third party imports
import tkinter as tk
from tkinter import ttk
# Local imports
from visuvia.mctp_comm import CommTask
from visuvia.utils.data_registry import DataRegistry
from ..gui.chartsmanager import ChartsManagerGUI
from ..gui.channelinfo import ChannelInfoGUI
from ..gui.textdisplay import TextDisplayGUI
from ..gui.orders import ConnManOrder


__all__ = ["ConnManagerGUI"]


class ConnManagerGUI():
    """
    GUI to start/stop MCTP data transfer, create/remove charts and display
    connection state and number of channels.
    Has methods to create, manage and place widgets on the window.

    Attributes:
        root (tk.Tk): The tk window.
        data_registry (DataRegistry): Data registy for the communication task.
        comm_task: MCTP communication task.
        chartman (ChartsManagerGUI): Charts manager.
        frame (tk.Frame): Base frame for this GUI.
        conn_status (tk.Label): Display MCTP connection status.
        ch_status (tk.Label): Display Number of channels.
        btn_start_transfer (tk.Button): Button that starts data transfer.
        btn_stop_transfer (tk.Button): Button that stops data transfer.
        btn_add_chart (tk.Button): Button that add charts.
        btn_remove_chart (tk.Button): Button that remove charts.
        save_var (tk.IntVar): Hold state of 'Save' button.
        chkbtn_save (tk.Checkbutton): Button to enable data save.

    Public Methods:
        place_widgets: Place widgets on the frame.
        start_comm: Start mctp communication.
        display_status_failed: Update GUI for failed connection.
        display_status_syncing: Update GUI for SYNC phase.
        display_status_connected: Update GUI for succesful connection.
        display_disable: Disable all buttons and menus.

    Internal Methods:
        _start_transfer: Callback for 'Start' button.
        _stop_transfer: Callback for 'Stop' button.
        _add_chart: Callback for '+' button.
        _remove_chart: Callback for '-' button.
    """
    def __init__(self, root, serial_ctrl):
        self.root = root 
        self.data_registry = DataRegistry()
        self.queue = Queue()

        self.comm_task = CommTask(serial_ctrl, self.data_registry, self)
        self.chartman_gui = ChartsManagerGUI(self.root, self.data_registry)
        self.ch_info_gui = ChannelInfoGUI(self.root, self.data_registry, 0.4)
        self.text_display_gui = TextDisplayGUI(self.root)

        # FRAME
        self.frame = tk.LabelFrame(
            master=root,
            text="Connection Manager",
            padx=5,
            pady=5,
            bg="lightgrey",
            relief="groove",
            bd=3,
            width=60)

        # STATIC WIDGETS
        lbl_sync = tk.Label(
            master=self.frame,
            text="STATUS",
            bg="lightgrey",
            fg="black",
            width=9,
        )
        lbl_sync.grid(column=0, row=0, sticky="se")
        lbl_ch = tk.Label(
            master=self.frame,
            text="CHANNELS",
            bg="lightgrey",
            fg="black",
            width=9,
        )
        lbl_ch.grid(column=0, row=1, padx=8, sticky="nsew")
        lbl_charts = tk.Label(
            master=self.frame,
            text="CHARTS",
            bg="lightgrey",
            fg="black",
            width=9,
            highlightthickness=0,
        )
        lbl_charts.grid(column=3, row=2)

        separator = ttk.Separator(self.frame, orient="vertical")
        separator.place(relx=0.47, rely=-0.15,
                        relwidth=0.001, relheight=1.2)

        # DYNAMIC WIDGETS
        self.lbl_conn_status = tk.Label(
            master=self.frame,
            text="IDLE",
            bg="black",
            fg="orange",
            relief="sunken",
            bd=2,
            width=12,
        )

        self.lbl_ch_status = tk.Label(
            master=self.frame,
            text="...",
            font=("TkDefaultFont", 12),
            bg="black",
            fg="orange",
            relief="sunken",
            bd=2,
            width=5,
        )
        self.btn_start_transfer = tk.Button(
            master=self.frame,
            text="Start \u25B6",
            state="disabled",
            bg="grey",
            relief="sunken",
            width=5,
            bd=2,
            highlightthickness=0,
            command=self._start_transfer
        )

        self.btn_stop_transfer = tk.Button(
            master=self.frame,
            text="Stop \u23F9",
            state="disabled",
            bg="grey",
            relief="sunken",
            width=5,
            bd=2,
            highlightthickness=0,
            command=self._stop_transfer
        )
        self.btn_add_chart = tk.Button(
            master=self.frame,
            text="+",
            state="disabled",
            width=5,
            bg="green",
            fg="white",
            bd=3,
            highlightthickness=0,
            command=self._add_chart
        )

        self.btn_remove_chart = tk.Button(
            master=self.frame,
            text="-",
            state="disabled",
            width=5,
            bg="#CC252C",
            fg="white",
            bd=3,
            highlightthickness=0,
            command=self._remove_chart
        )

        self.save_var = tk.IntVar()
        self.chkbtn_save = tk.Checkbutton(
            master=self.frame, text="Save",
            variable=self.save_var,
            onvalue=1, offvalue=0, bg="lightgrey",
            state="disabled",
        )

        self.process_queue()

    def process_queue(self):
        """
        """
        while not self.queue.empty():
            order, arg = self.queue.get()
            match ConnManOrder(order):
                case ConnManOrder.STATUS_FAILED:
                    self.display_status_failed()
                case ConnManOrder.STATUS_SYNCING:
                    self.display_status_syncing()
                case ConnManOrder.STATUS_CONNECTED:
                    self.display_status_connected(arg)
                case ConnManOrder.APPEND_TEXT:
                    self.text_display_gui.append_text(arg)
                case ConnManOrder.CH_INFO_UPDATE:
                    self.ch_info_gui.update_info(arg)
                case ConnManOrder.CH_INFO_DRAW:
                    self.ch_info_gui.draw()
        # Check queue every 100ms
        self.root.after(100, self.process_queue)

    def place_order(self, order, arg=None):
        """
        """
        self.queue.put((order, arg))

    def place_widgets(self):
        """
        Place frame and all widgets.
        """
        self.frame.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        self.lbl_conn_status.grid(column=1, row=0, sticky="sw")

        self.lbl_ch_status.grid(column=1, row=1, sticky="w")

        self.btn_start_transfer.grid(column=2, row=0, padx=25,
                                     sticky="s")
        self.btn_stop_transfer.grid(column=2, row=1, rowspan=1, padx=25,
                                    sticky="n")

        self.btn_add_chart.grid(column=3, row=0, sticky="s")
        self.btn_remove_chart.grid(column=3, row=1, sticky="n")

        self.chkbtn_save.grid(column=2, row=2)

        self.text_display_gui.place_widgets()

    def start_comm(self):
        """
        Start MCTP communication.
        """
        self.comm_task.start()
        self.comm_task.place_order("sync")

    def display_status_connected(self, channels_n):
        """
        Updates GUI after successful connection.
        """
        self.lbl_conn_status["text"] = "CONNECTED"
        self.lbl_conn_status["fg"] = "lightgreen"

        self.lbl_ch_status["text"] = str(channels_n)
        self.lbl_ch_status["fg"] = "lightgreen"

        # Enables data transfer related options
        self.btn_stop_transfer.config(state="disabled", relief="sunken",
                                      bg="grey", fg="black")
        self.btn_start_transfer.config(state="normal", relief="raised",
                                       bg="lightgrey", fg="black")
        if channels_n > 0:
            self.btn_add_chart["state"] = "normal"
            self.btn_remove_chart["state"] = "normal"
            self.chkbtn_save["state"] = "normal"

    def display_status_syncing(self):
        """
        Updates GUI after start of sync phase.
        """
        self.lbl_conn_status["text"] = "SYNC"
        self.lbl_conn_status["fg"] = "cyan"

        self.lbl_ch_status["text"] = "..."
        self.lbl_ch_status["fg"] = "cyan"

        self.btn_start_transfer["state"] = "disabled"
        self.btn_stop_transfer["state"] = "disabled"
        self.btn_add_chart["state"] = "disabled"
        self.btn_remove_chart["state"] = "disabled"
        self.chkbtn_save["state"] = "disabled"

    def display_status_failed(self):
        """
        Updates GUI after failed connection.
        """
        self.lbl_conn_status["text"] = "Failed"
        self.lbl_conn_status["fg"] = "red"

        self.lbl_ch_status["text"] = "..."
        self.lbl_ch_status["fg"] = "red"

        self.btn_start_transfer["state"] = "disabled"
        self.btn_stop_transfer["state"] = "disabled"
        self.btn_add_chart["state"] = "disabled"
        self.btn_remove_chart["state"] = "disabled"
        self.chkbtn_save["state"] = "disabled"

    def display_disable(self):
        """
        Destroy charts and disable all buttons.
        """
        self.comm_task.place_order("drop")
        self.comm_task.stop()
        self.chartman_gui.reset()
        self.data_registry.clear_channels()

        self.lbl_conn_status["text"] = "IDLE"
        self.lbl_conn_status["fg"] = "orange"

        self.lbl_ch_status["text"] = "..."
        self.lbl_ch_status["fg"] = "orange"
        self.btn_stop_transfer.config(state="disabled", relief="sunken",
                                      bg="grey", fg="black")
        self.btn_start_transfer.config(state="disabled", relief="sunken",
                                       bg="grey", fg="black")
        self.btn_add_chart.config(state="disabled")
        self.btn_remove_chart.config(state="disabled")

        self.ch_info_gui.close()

    def _start_transfer(self):
        """
        Start requesting data from performer. Callback for the 'Start' button.
        """
        self.data_registry.clear_data()
        self.text_display_gui.reset()

        # Send request frame to MCU
        self.comm_task.place_order("request")
        # Initialize plotting thread
        self.chartman_gui.init_plot_task()

        self.btn_stop_transfer.config(state="normal", relief="raised",
                                      bg="lightgrey", fg="black")
        self.btn_start_transfer.config(state="disabled", relief="sunken",
                                       bg="grey", fg="black")

    def _stop_transfer(self):
        """
        Stop requesting data from performer. Callback for the 'Stop' button.
        """
        self.chartman_gui.stop_plot_task()
        self.comm_task.place_order("stop")

        if self.save_var.get():
            self.data_registry.save_data()

        self.btn_stop_transfer.config(state="disabled", relief="sunken",
                                      bg="grey")
        self.btn_start_transfer.config(state="normal", relief="raise",
                                       bg="lightgrey")
        self.ch_info_gui.draw()

    def _add_chart(self):
        """
        Append chart to GUI. Callback for the '+' button.
        """
        self.chartman_gui.add_chart()

    def _remove_chart(self):
        """
        Remove chart from GUI. Callback for the '-' button.
        """
        self.chartman_gui.remove_chart()
