"""
This module provides the ChartsManagerGUI and the ChartGUI classes.

The ChartsManagerGUI class manages the creation of multiple ChartGUI's.
It controls how to place the charts on the screen and when to start/stop
the plottings for all it's charts.

The ChartGUI class manages a single chart and all it's associated
widgets. It has methods to place and remove the widgets and to start
and stop the data plotting on the chart.

Dependencies:
- matplotlib
- tkinter
"""


# Third party imports
import tkinter as tk
import matplotlib.pyplot as pplt
from matplotlib.animation import FuncAnimation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg


__all__ = ["ChartsManagerGUI", "ChartGUI"]


line_colors = [
    'red', 'green', 'blue', 'yellow', 'cyan', 'magenta', 'black', 'white',
    'orange', 'purple', 'brown', 'pink', 'gray', 'lightblue', 'lime', 'violet'
]
graph_types = ["Normal", "Scatter", "Oscilloscope"]
filters = ["-"]


class ChartsManagerGUI():
    """
    Manage the creation, removal and placing of multiple charts on the window.
    Has methods to add and remove charts in LIFO. Creates up to 6 charts in 3x2
    in the grid. Also has methods to start and stop plotting on the charts.

    Attributes:
        root (tk.Tk): The tk window.
        data_registry (DataRegistry): The data registry. Source of plot data.
        plotting (bool): Set when plotting, clear when idle.
        charts (list[ChartGUI]): List of charts managed.
        frame: Base frame for the charts.

    Public Methods:
        init_plot_task: Start plotting on all charts.
        stop_plot_task: Stop plotting on all charts.
        add_chart: Append new chart to the frame.
        remove_chart: Remove last created chart from the frame.
        reset: Stop plotting and remove all charts.

    Internal Methods:
        _adjust_charts: Adjust charts placing on the grid.
    """
    def __init__(self, root, data_registry):
        self.root = root 
        self.data_registry = data_registry
        # For charts created during plotting
        self.plotting = False

        # list of chart data for each chart
        self.charts = []

        self.frame = tk.Frame(self.root, bg="lightgrey", bd=5,
                              relief=tk.GROOVE)
        self.frame.grid(row=0, column=1, padx=10, pady=10,
                        rowspan=4, sticky="nsew")

    def init_plot_task(self):
        """
        Start plotting animation on all charts.

        Returns:
            None: Returns nothing.
        """
        if self.plotting:
            return
        self.plotting = True

        for chart in self.charts:
            chart.clear_plot()
            chart.start_ani()

    def stop_plot_task(self):
        """
        Stop plotting animation on all charts.

        Returns:
            None: Returns nothing.
        """
        if not self.plotting:
            return
        self.plotting = False

        for chart in self.charts:
            chart.stop_ani()

    def add_chart(self):
        """
        Place new chart on the frame.

        Returns:
            None: Returns nothing.
        """
        if len(self.charts) >= 6:
            # TODO: new tab
            return

        frame = tk.LabelFrame(
            master=self.frame,
            text=f"Chart {len(self.charts)+1}",
            padx=5, pady=5, bg="lightgrey")

        column = int(len(self.charts) / 3)
        row = len(self.charts) % 3
        frame.grid(padx=5, column=column, row=row, sticky="nsew")

        new_chart = ChartGUI(frame, self.data_registry)
        new_chart.place_widgets()

        if self.plotting:
            new_chart.start_ani()

        # Only append chart after setting it because of the plot thread.
        self.charts.append(new_chart)
        self._adjust_charts()

    def remove_chart(self):
        """
        Remove last created chart from the frame.

        Returns:
            None: Returns nothing.
        """
        if len(self.charts) > 0:
            chart = self.charts.pop()
            chart.remove()
        self._adjust_charts()

    def reset(self):
        """
        Stop plot task and remove all charts.

        Returns:
            None: Returns nothing.
        """
        self.stop_plot_task()
        for chart in self.charts:
            chart.remove()

        self.charts = []

    def _adjust_charts(self):
        """
        Resize charts on window based on the number of charts.
        """
        for column in range(self.frame.grid_size()[0]):
            self.frame.grid_columnconfigure(column, weight=0)
        for row in range(self.frame.grid_size()[1]):
            self.frame.grid_rowconfigure(row, weight=0)

        n = len(self.charts)
        for row in range(min(n, 3)):
            self.frame.grid_rowconfigure(row, weight=1)
        for column in range(int(n/4)+1):
            self.frame.grid_columnconfigure(column, weight=1)


class ChartGUI():
    """
    Manages a single chart widget on the GUI. Has control over all widgets
    inside a chart and methods to place the widgets, start/stop the plot
    animation and clear the plot.

    Attributes:
        frame (tk.Frame): Frame for the chart widgets.
        data_registry (DataRegistry): The data registry. Source of plot data.
        fig (pplt.Figure): Figure for the plot.
        canvas (FigureCanvasTkAgg): Canvas for the plot.
        canvas_widget (tk.Widget): Tk widget for the plot.
        axes (pplt.Axes): Axes for the plot.
        ani (FuncAnimation): Plot animation.
        checkbox_vars (dict[int, tk.Intvar()): Dict of checkbox states for each
        channel.
        graph_type_var (tk.StringVar()): StringVar with type selected by the
        graph type menu.
        filter_var (tk.StringVar()): StringVar with filter selected by the
        filter menu.
        oscilloscope (bool): Set for oscilloscope mode, clear for normal.
        interval (float): Time interval shown in plot on oscilloscope mode.

    Public Methods:
        place_widgets: Put all widgets on the frame.
        start_ani: Start plotting animation.
        stop_ani: Stop plotting animation.
        clear_plot: Clear all lines.
        destroy: Destroy the frame and all widgets.

    Internal Methods:
        _place_graph: Place pyplot graph widget.
        _place_channel_menu: Place channel selector menu widgets.
        _place_type_menu: Place plot type drop menu widget.
        _place_filter_menu: Place filter type drop menu widget.

    Private Methods:
        __type_menu_callback: Callback for plot type drop menu.
        __btn_ch_selector_toggle: Toggle behavior for channel selector buttons.
        __get_time_interval: Get number of samples for oscilloscope mode.
        __update_lines: Generate lines for the animation.
    """
    def __init__(self, frame, data_registry):
        self.frame = frame
        self.data_registry = data_registry

        self.fig = pplt.Figure(dpi=80, facecolor="darkgray")
        self.canvas = FigureCanvasTkAgg(self.fig, master=self.frame)
        self.canvas_widget = self.canvas.get_tk_widget()
        self.axes = self.fig.add_subplot(111, facecolor="black")
        self.lines = {}
        self.ani = None

        self.checkbox_vars = {}
        self.graph_type_var = tk.StringVar()
        self.filter_var = tk.StringVar()
        self.oscilloscope = False
        self.entry_interval = None
        self.interval = 0.3       # in Seconds

    def place_widgets(self):
        """
        Place all chart widgets on the frame.

        Returns:
            None: Returns nothing.
        """
        self._place_graph()
        self._place_channel_menu()
        self._place_type_menu()
        self._place_filter_menu()
        self._place_interval_entry()
        self.__interval_scroll_event()

    def start_ani(self, framerate=30):
        """
        Stop plotting animation on the chart figure.

        Parameters:
            framerate (int): The framerate for the animation in fps.
            Defaults to 30.

        Returns:
            None: Returns nothing.
        """
        if self.ani is not None:
            return
        interval = (1/framerate) * 1000
        self.ani = FuncAnimation(self.fig, self.__update_lines,
                                 frames=None, interval=interval, blit=True,
                                 cache_frame_data=False)

    def stop_ani(self):
        """
        Start plotting animation on the chart figure.

        Returns:
            None: Returns nothing.
        """
        if self.ani is not None:
            self.ani.event_source.stop()
            self.ani.event_source = None
            self.ani = None

        for line in self.lines.values():
            line.set_animated(False)

        # 0 is just a dummy value for this function to work.
        self.__update_lines(0)
        self.canvas.draw()

    def clear_plot(self):
        """
        Clear all lines.

        Returns:
            None: Returns nothing.
        """
        for line in self.lines.values():
            line.set_data([], [])

    def remove(self):
        """
        Remove all widgets and destroy frame.

        Returns:
            None: Returns nothing.
        """
        if self.ani is not None:
            self.ani.event_source.stop()
        for widget in self.frame.winfo_children():
            widget.grid_forget()
            widget.destroy()
        self.frame.destroy()

    def _place_graph(self):
        """
        Place axes and canvas widgets on frame.

        Returns:
            None: Returns nothing.
        """
        self.axes.grid(visible=True, which='both', linestyle='--',
                       color="white", alpha=0.7)

        self.axes.set_xlim(0, 10)
        self.axes.set_ylim(-10, 10)

        self.canvas_widget.grid(column=1, row=1, columnspan=3, sticky="nsew")
        self.canvas_widget.config(bg="lightgrey", relief="sunken", bd=4)

        self.frame.grid_columnconfigure(1, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)

        # Initialize lines with empty plots.
        for ch_id in list(self.data_registry.channels.keys()):
            line, = self.axes.plot([], [], 'b-', label=str(ch_id),
                                   animated=True)
            line.set_color(line_colors[ch_id])
            self.lines[ch_id] = line

    @staticmethod
    def __btn_ch_selector_toggle(button, var):
        """
        Button callback to make it behave as toggle button.
        Sets var when it is cleared an clears it when it is set.

        Parameters:
            button (tk.Button): The button.
            var (tk.IntVar()): The var associated with the button.

        Returns:
            None: Returns nothing.
        """
        if var.get():  # If variable is True
            var.set(False)
            button.config(relief="raised", bg="lightgrey")
        else:  # If variable is False
            var.set(True)
            button.config(relief="sunken", bg="lightgreen")

    def _place_channel_menu(self):
        """
        Place menu with toggle buttons for each channel enabling/disabling.

        Returns:
            None: Returns nothing.
        """
        ch_menu_frame = tk.LabelFrame(
            master=self.frame,
            text="Available Channels",
            bg="lightgrey")
        ch_menu_frame.grid(column=0, row=0, rowspan=2,
                           padx=5, pady=5, sticky="N")

        button_count = 0
        for ch_id in list(self.data_registry.channels.keys()):
            row = int(button_count / 2)
            column = button_count % 2

            self.checkbox_vars[ch_id] = tk.IntVar()
            var = self.checkbox_vars[ch_id]

            toggle_button = tk.Button(
                ch_menu_frame,
                text=f"CH{ch_id}",
                relief="raised",
                bd=2)

            toggle_button.config(
                command=lambda button=toggle_button,
                var=var: self.__btn_ch_selector_toggle(button, var)
            )
            toggle_button.grid(row=row, column=column, padx=5)
            button_count += 1

    @staticmethod
    def __validate_interval(value):
        if value == "":
            return True
        try:
            number = float(value)
            if 0 <= number <= 999:
                return True
        except ValueError:
            return False

        return False

    def __store_entry_value(self, event):
        """Callback to store entry value when Enter is pressed."""
        self.interval = float(self.entry_interval.get())
        print(self.interval)

    def __increase_interval(self, event):
        if self.oscilloscope:
            self.interval += 0.1
            self.interval = min(self.interval, 10)
            self.entry_interval.delete(0, tk.END)
            self.entry_interval.insert(0, round(self.interval, 2))
            self.axes.set_xlim(0, self.interval)
            self.canvas.draw()

    def __decrease_interval(self, event):
        if self.oscilloscope:
            self.interval -= 0.1
            self.interval = max(self.interval, 0.1)
            self.entry_interval.delete(0, tk.END)
            self.entry_interval.insert(0, round(self.interval, 2))
            self.axes.set_xlim(0, self.interval)
            self.canvas.draw()

    def _place_interval_entry(self):
        validate_interval = self.frame.master.master.register(
            self.__validate_interval
        )

        lbl_interval = tk.Label(self.frame, text="Interval:")
        lbl_interval.grid(row=0, column=2)

        self.entry_interval = tk.Entry(
            self.frame,
            width=5,
            justify="right",
            validate="key",
            state="disabled",
            validatecommand=(validate_interval, "%P"))
        self.entry_interval.bind("<Return>", self.__store_entry_value)
        self.entry_interval.grid(row=0, column=3, sticky="e")

    def __interval_scroll_event(self):
        # Scroll up (Linux)
        widgets = [self.frame, self.canvas_widget, self.entry_interval]
        for widget in widgets:
            widget.bind("<Button-4>", self.__increase_interval)
            widget.bind("<Button-5>", self.__decrease_interval)

    def _place_filter_menu(self):
        # TODO: Implement this feature from here.
        """
        Place drop menu with filter options.

        Returns:
            None: Returns nothing.
        """
        self.filter_var.set(filters[0])

        drop_filter = tk.OptionMenu(
            self.frame,
            self.filter_var,
            *filters,
            command=self.__dummy)
        drop_filter.config(width=10)

        # drop_filter.grid(row=1, column=2, sticky="sw")

    def _place_type_menu(self):
        """
        Place drop menu with graph type options.

        Returns:
            None: Returns nothing.
        """
        self.graph_type_var.set(graph_types[0])

        drop_type = tk.OptionMenu(
            self.frame,
            self.graph_type_var,
            *graph_types,
            command=self.__type_menu_callback)
        drop_type.config(width=10)

        drop_type.grid(row=0, column=1, sticky="se")

    def __type_menu_callback(self, widget):
        """
        Callback for graph type drop menu. Changes the plotting display
        based on the selected option.
        """
        # Normal
        if self.graph_type_var.get() == graph_types[0]:
            self.oscilloscope = False
            self.entry_interval.delete(0, tk.END)
            self.entry_interval.config(state="disabled")
        # Scatter
        elif self.graph_type_var.get() == graph_types[1]:
            self.oscilloscope = False
            self.entry_interval.delete(0, tk.END)
            self.entry_interval.config(state="disabled")
        # Oscilloscope
        elif self.graph_type_var.get() == graph_types[2]:
            self.oscilloscope = True
            self.axes.set_ylim(-10, 10)
            self.axes.set_xlim(0, self.interval)
            self.canvas.draw_idle()
            self.entry_interval.config(state="normal")
            self.entry_interval.delete(0, tk.END)
            self.entry_interval.insert(0, round(self.interval, 2))

    def __dummy(self, widget):
        # TODO: update graph
        pass

    def __get_time_interval(self, arr, interval):
        """
        Finds the number of samples in the array for the given interval.
        It iterates through the array in reverse order until the times
        in the list go past the interval or until it reaches the start of
        the array.

        Parameters:
            arr (list[float]): Array with times in seconds in crescent order.
            interval (float): The interval for which it will count samples.

        Returns:
            int: the number of samples in the array for the interval.
        """
        time_ref = arr[-1]
        base_time = time_ref-interval
        if base_time < 0:
            return 1

        sample_count = 0
        for item in reversed(arr):
            if item > base_time:
                sample_count += 1

        return sample_count

    def __update_lines(self, frame):
        """
        Callback for the plot animation with blitting enabled. Creates
        lines based on the graph type with data from the data registry.
        Updates the graph to simulate real-time plotting behavior. This
        is done every 10 frames for optimization.
        The tk window is updated every frame from here to reduce lag.

        Parameters:
            frame (tk.Frame): The frame where the animation runs.

        Returns:
            list[]: List with matplotlib artists to be redrawn. Lines and
            legend.
        """
        if frame % 10 == 0 and not self.oscilloscope:
            self.canvas.draw()
        # Update window
        self.frame.master.master.update_idletasks()

        artists = []
        legend = self.axes.get_legend()
        if legend:
            legend.remove()
        xlim_end = 0.001
        # TODO: ylimiters based on acquired data ylim_end = 0
        # Better make this when appending data on registry.
        for ch_id, plot_data in self.data_registry.channels.items():
            var = self.checkbox_vars.get(ch_id)
            line = self.lines[ch_id]
            if var and var.get():
                if len(plot_data.x_data) == 0:
                    continue
                if len(plot_data.x_data) != len(plot_data.y_data):
                    # FIXME: find out what is causing this issue.
                    # Possibly need to implement locks on data_registry.
                    print("Unequal x_data and y_data length")
                    break

                # Channels may have different time intervals.
                xlim_end = max(xlim_end, plot_data.x_data[-1])

                line = self.lines[ch_id]
                if self.oscilloscope:
                    n_of_samples = self.__get_time_interval(plot_data.x_data,
                                                            self.interval)

                    line.set_data(plot_data.x_data[-n_of_samples:],
                                  plot_data.y_data[-n_of_samples:])
                else:
                    line.set_data(plot_data.x_data, plot_data.y_data)

                line.set_label(str(ch_id))
                # active_lines.append(line)
            else:
                line.set_label("")
                line.set_data([], [])
            artists.append(self.lines[ch_id])

        if self.oscilloscope:
            self.axes.set_xlim(max(0, xlim_end-self.interval), xlim_end)
        else:
            self.axes.set_xlim(0, xlim_end)
        self.axes.set_ylim(-10, 10)

        artists.append(self.axes.legend(loc="upper right"))

        return artists
