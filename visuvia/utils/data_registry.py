"""
This module provides the DataRegistry object.

The DataRegistry object holds all numerical data acquired during data transfer
in an array and creates an array with estimated times for each sample. It is
meant to hold data for time domain plotting. It also holds text data in a
string.

Dependencies:
- numpy
"""

# Standard library imports
from dataclasses import dataclass
import time
import csv
# Third party imports
import numpy as np


__all__ = ["DataRegistry"]


@dataclass
class DataChannel():
    """
    Hold channel data and time info. Used inside DataRegistry.

    Attributes:
        x_data (np.array): Time data for the x axis.
        y_data (np.array): Data for the y axis.
        recv_time (float): Time when current data was appended, relative
                           to start_time_ref of the registry.
    """
    recv_time: float
    x_data: np.array
    y_data: np.array
    text: str

    def __str__(self):
        dc_str = f"{self.x_data.__str__()}\n"
        dc_str += self.y_data.__str__()
        return dc_str


class DataRegistry():
    """
    Control and registry of all data channels.

    Attributes:
        channels (dict[int, PlotData]):
        start_time_ref (float):
    """
    def __init__(self):
        self.channels: dict[int, DataChannel] = {}
        self.start_time_ref = 0

    def add_channel(self, ch_id):
        """
        Add new empty channel to the registry. Overwrites if channel
        was added previously.

        Args:
            ch_id: Channel number/ID.

        Returns:
            None: Returns nothing.
        """
        new_channel = DataChannel(0, np.array([]), np.array([]), "")
        self.channels[ch_id] = new_channel

        print(f"Channel {ch_id} added.")

    def set_time_ref(self):
        """
        Set initial time reference for plotting. Meant to be the time
        when the transfer phase starts.

        Returns:
            None: Returns nothing.
        """
        self.start_time_ref = time.time()

    def append_data(self, frame_data):
        """
        Append new data to registry.

        Args:
            frame_data (dict[int | list]): Dictionary where keys are channels
            and values are data to be appended to that channel. This is meant
            to be the data_channels dict from a parsed DATA frame.

        Returns:
            None: Returns nothing.
        """
        # Time since the time reference.
        relative_time = time.time() - self.start_time_ref

        for ch_id, ch_data in frame_data.items():
            channel = self.channels[ch_id]
            # Time between frames for each channel
            full_period = relative_time - channel.recv_time
            # Create and append time array for channel
            channel.x_data = np.append(
                channel.x_data,
                np.array(self.__generate_time_array(ch_data, full_period,
                                                    channel.recv_time))
            )
            channel.recv_time += full_period

            # Append value array for channel
            channel.y_data = np.append(channel.y_data, np.array(ch_data))

    def append_text(self, frame_text_data):
        """
        Append new text to registry.

        Args:
            frame_data (dict[int | list]): Dictionary where keys are channels
            and values are the texts to be appended to that channel. This is
            meant to be the text_channels dict from a parsed DATA frame.

        Returns:
            None: Returns nothing.
        """
        relative_time = time.time() - self.start_time_ref

        for ch_id, ch_text in frame_text_data.items():
            channel = self.channels[ch_id]
            channel.text += ch_text + "\n"

            full_period = relative_time - channel.recv_time
            channel.recv_time += full_period

    def save_data(self):
        """
        Write data from all channels containing plot and/or text data to csv
        and txt files.

        Returns:
            None: Returns nothing.
        """
        print("Saving data")
        for ch_id, channel in self.channels.items():
            if channel.x_data.size == 0:
                continue
            filename = f"channel_{ch_id}.csv"
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                for x, y in zip(channel.x_data, channel.y_data):
                    writer.writerow([x, y])
                print(f"Data written to {filename}")

        for ch_id, channel in self.channels.items():
            if channel.text == "":
                continue
            filename = f"channel_{ch_id}.txt"
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                file.write(channel.text)
                print(f"Text data written to {filename}")

    def clear_data(self):
        """
        Clear data from all channels

        Returns:
            None: Returns nothing.
        """
        for _, channel in self.channels.items():
            channel.x_data = np.array([])
            channel.y_data = np.array([])
            channel.text = ""
            channel.recv_time = 0

    def clear_channels(self):
        """
        Remove all channels.

        Returns:
            None: Returns nothing.
        """
        self.channels = {}
        self.start_time_ref = None

    @staticmethod
    def __generate_time_array(arr, full_period, start_time):
        """
        Generate an array of times based on the input array,
        the period and start time reference.

        Args:
            arr (list[int | float]): Input array.
            full_period (float): The time interval for the entire array.
            start_time (float): The starting time reference for the array.
            The time where the sampling for this array began.

        Returns:
            list[float]: Generated array of times.
        """
        period = full_period / (len(arr))
        return [start_time + period * x for x in range(len(arr))]
