"""
Describe this module
"""

import time
# Third party imports
import tkinter as tk


__all__ = ["ChannelInfoGUI"]


class ChannelInfoGUI():
    """
    Describe this class
    """
    def __init__(self, window, data_registry, draw_interval):
        self.frame = tk.LabelFrame(
            window, bg="lightgrey", height=30, relief="groove",
            width=300, bd=4, text="Channel Info")
        self.data_registry = data_registry
        self.draw_interval = draw_interval

        self.intervals = {}
        self.intervals_canvas = []
        self.intervals_texts = {}

        self.sizes = {}
        self.sizes_canvas = []
        self.sizes_texts = {}

        self.last_draw_time = time.time()

        self.ch_interval_frame = tk.LabelFrame(
            self.frame, bg="lightgrey", height=30,
            width=300, bd=3, padx=1, pady=5,
            text="Data receive interval")
            # TODO: (optional) Show frequency.

        self.ch_size_frame = tk.LabelFrame(
            self.frame, bg="lightgrey", height=30,
            width=300, bd=3, padx=1, pady=5,
            text="Number of samples")

        self.frame.grid_rowconfigure(0, weight=1)
        self.frame.grid_rowconfigure(1, weight=1)
        self.frame.grid(row=2, column=0, padx=10, pady=10)

        self.ch_interval_frame.grid(row=0, column=0, sticky="nsew")
        self.ch_size_frame.grid(row=1, column=0, sticky="nsew")

    def place_channel_info(self):
        """
        Describe this method
        """
        n_of_channels = len(self.data_registry.channels)

        # Create one canvas for every 8 channels
        for i in range(0, n_of_channels, 8):
            # Intervals
            canvas_intervals = tk.Canvas(
                self.ch_interval_frame,
                bg="black",
                width=36*n_of_channels,
                height=10,
                bd=2,
                relief="sunken"
            )
            row = int(1 + i/8)
            canvas_intervals.grid(row=row, column=0, columnspan=n_of_channels)
            self.intervals_canvas.append(canvas_intervals)

            # Sizes
            canvas_sizes = tk.Canvas(
                self.ch_size_frame,
                bg="black",
                width=36*n_of_channels,
                height=10,
                bd=2,
                relief="sunken"
            )
            row = int(1 + i/8)
            canvas_sizes.grid(row=row, column=0, columnspan=n_of_channels)
            self.sizes_canvas.append(canvas_sizes)

        # Create one text_id per channel
        count = 0
        for ch_id in self.data_registry.channels.keys():
            row = int(count/8)
            column = count % 8

            # INTERVALS MENU
            canvas = self.intervals_canvas[row]
            lbl_ch_name_intervals = tk.Label(
                self.ch_interval_frame, bg="lightgrey",
                text=f"CH_{ch_id}"
            )
            lbl_ch_name_intervals.grid(row=row, column=column,
                                       padx=1, sticky="w")

            text_id = canvas.create_text(
                17 + 36*count, 8,
                text="0",
                fill="red",
                font=("TkDefaultFont", 11)
            )
            self.intervals_texts[ch_id] = text_id

            # SIZES MENU
            canvas = self.sizes_canvas[row]
            lbl_ch_name_sizes = tk.Label(
                self.ch_size_frame, bg="lightgrey",
                text=f"CH_{ch_id}"
            )
            lbl_ch_name_sizes.grid(row=row, column=column,
                                   padx=1, sticky="w")

            text_id = canvas.create_text(
                17 + 36*count, 8,
                text="0",
                fill="cyan",
                font=("TkDefaultFont", 11)
            )
            self.sizes_texts[ch_id] = text_id

            count += 1

    def draw(self):
        # TODO: Error if labels were not created for these channels.
        """
        Describe this method
        """
        self.frame.master.update_idletasks()
        cur_time = time.time()
        if cur_time - self.last_draw_time < self.draw_interval:
            return

        count = 0
        for ch_id, interval in self.intervals.items():
            canvas = self.intervals_canvas[int(count/8)]
            text_id = self.intervals_texts[ch_id]
            canvas.itemconfig(text_id, text=f"{round(interval, 3)}")
            count += 1

        count = 0
        for ch_id, size in self.sizes.items():
            canvas = self.sizes_canvas[int(count/8)]
            text_id = self.sizes_texts[ch_id]
            canvas.itemconfig(text_id, text=f"{size}")
            count += 1

        self.last_draw_time = cur_time

    def update_info(self, updated_channels):
        # NOTE: For this to work, this method must be called before
        # the incoming data is appended to registry.
        """
        Describe this method
        """
        if not self.intervals_canvas or not self.sizes_canvas:
            # Attempt to update without placing info first.
            return
        cur_time = time.time()
        for ch_id in updated_channels:
            # Intervals info
            channel = self.data_registry.channels[ch_id]
            previous_recv = channel.recv_time
            interval = (cur_time - previous_recv -
                        self.data_registry.start_time_ref)
            self.intervals[ch_id] = round(interval, 3)

            # Size info
            size = len(channel.x_data) + len(channel.text)
            self.sizes[ch_id] = size

    def close(self):
        """
        Describe this method
        """
        for widget in self.ch_size_frame.winfo_children():
            widget.grid_forget()
            widget.destroy()
        for widget in self.ch_interval_frame.winfo_children():
            widget.grid_forget()
            widget.destroy()

        self.intervals = {}
        self.intervals_canvas = []
        self.intervals_texts = {}

        self.sizes = {}
        self.sizes_canvas = []
        self.sizes_texts = {}
