"""
This module provides the CommTask class.

The CommTask implements the MCTP controller side finite state machine,
which handles MCTP connection between performer and controller. It
works independently as a thread and contains methods to start and
stop the thread, as well as methods for user-triggered events of the
finite state machine.
"""

# TODO: Make queue gui-agnostic, so that the same queue can be used by
# tkinter, cmd application and any other interfaces. Let the queue be
# inside the class, so that the interface checks inside the task instead
# of the task appending to a gui queue.
# TODO: stop immediately if SerialCtrlError occurs

# Standard library imports
import sys
import time
import threading
from enum import Enum
from queue import Queue
# Third Party imports
# from crccheck.crc import Crc32, CrcXmodem
# Local imports
from visuvia.utils.mctp import MCTPFrame, MCTPParseError, serialize_frame
from visuvia.gui.orders import ConnManOrder, CommTaskOrder
from visuvia.utils.serial_ctrl import SerialCtrlError


__all__ = ["CommTask", "CommTaskState"]


class CommTaskState(Enum):
    """
    Identifier for the state of the communication task finite state machine
    """
    IDLE = 1
    SYNC = 2
    CONNECTED = 3
    TRANSFER = 4

    def __str__(self):
        return self.name

class TimeoutHandler():
    def __init__(self):
        self.timeouts = {
            "sync": None,
            "ping": None,
            "stop": None,
            "drop": None,
            "end_task": None,
        }
        self.start_times = {
            "sync": None,
            "ping": None,
            "stop": None,
            "drop": None,
            "end_task": None,
        }

    def set_timeout(self, frame_type, timeout):
        """ Start timeout count for the type"""
        self.timeouts[frame_type] = timeout
        self.start_times[frame_type] = time.time()

    def check_timeout(self, frame_type):
        """ Start timeout count for the type"""
        timeout = self.timeouts[frame_type]
        if timeout is None:
            print("Error: Checking unitialized timer")
            return False

        start_time = self.start_times[frame_type]

        if time.time() - start_time > timeout:
            self.timeouts[frame_type] = None
            self.start_times[frame_type] = 0
            return True

        return False

    def is_enabled(self, frame_type):
        return bool(self.timeouts[frame_type])


class CommTask():
    """
    Finite state machine for serial connection

    Args:
        serial_ctrl (SerialCtrl): Initialized serial controller for serial
                                  communication.
        data_registry (DataRegistry): Data registry to which incoming data will
                                      be appended.
        connman_gui (ConnManagerGUI, optional): GUI to display connection
                                                status.

    Attributes:
        serial_ctrl (SerialCtrl): Initialized serial controller for serial
                                  communication.
        data_registry (DataRegistry): Data registry to which incoming data
                                      will be appended.
        connman_gui (ConnManagerGUI): GUI to display connection status.
        state (CommTaskState): State of the communication task finite
                               state machine.
        thread (threading.Thread): CommTask thread.
        update (threading.Condition()): Condition to notify state
                                              change to the thread.
        running (bool): Set when thread is running. Control thread execution.
    """
    def __init__(self, serial_ctrl, data_registry, connman_gui=None):
        self.state = CommTaskState.IDLE
        self.serial_ctrl = serial_ctrl
        self.data_registry = data_registry
        self.connman_gui = connman_gui

        self.thread = None
        self.update = threading.Condition()
        self.running = False

        self.frames_received = 0
        self.bytes_received = 0

        self.order_queue = Queue()
        self.timeouts = TimeoutHandler()

    def start(self):
        """
        Start communication task thread.

        Returns:
            None: Returns nothing.
        """
        self.running = True
        self._set_state(CommTaskState.IDLE)
        self.thread = threading.Thread(target=self.__run, daemon=True)
        self.thread.start()

    def stop(self):
        """
        Stop communication task thread

        Returns:
            None: Returns nothing.
        """
        self.timeouts.set_timeout("end_task", 2)
        while not self.order_queue.empty():
            if self.timeouts.check_timeout("end_task"):
                print("Warning: Task orders taking too long to end. " +
                      "Closing without attending")

        self.running = False
        self._set_state(CommTaskState.IDLE)
        self.thread.join()

    def place_order(self, order):
        match order:
            case "sync":
                if self.connman_gui is not None:
                    self.connman_gui.place_order(ConnManOrder.STATUS_SYNCING)
                if self.state == CommTaskState.IDLE:
                    self._set_state(CommTaskState.SYNC)
            case "request":
                self.order_queue.put(CommTaskOrder.REQUEST)
                with self.update:
                    self.update.notify()
            case "stop":
                self.order_queue.put(CommTaskOrder.STOP)
                with self.update:
                    self.update.notify()
            case "drop":
                self.order_queue.put(CommTaskOrder.DROP)
                with self.update:
                    self.update.notify()

    def __application_event_handler(self):
        """
        Check for application-trigerred events.

        Returns:
            None: Returns nothing.
        """
        while not self.order_queue.empty():
            order = self.order_queue.get()
            match order:
                case CommTaskOrder.REQUEST:
                    if self.state != CommTaskState.CONNECTED:
                        continue

                    self._set_state(CommTaskState.TRANSFER)

                    req_frame = serialize_frame(frame_type="request")
                    self.serial_ctrl.send(req_frame)
                    # Initialize time reference for plotting.
                    # This disconsiders the time for the request frame to
                    # arrive and the time for MCU to start sending data after
                    # being notified.
                    # FIXME: Use a dummy RDY packet to set reference for plot.
                    self.data_registry.set_time_ref()

                case CommTaskOrder.STOP:
                    if self.state != CommTaskState.TRANSFER:
                        continue
                    self.__stop_loop()
                    self.frames_received = 0
                    self.bytes_received = 0
                case CommTaskOrder.DROP:
                    self.__drop_loop()

    def __run(self):
        """
        Communication task thread. Implements the MCTP controller side finite
        state machine

        Returns:
            None: Returns nothing.
        """

        while self.running:

            with self.update:
                self.__application_event_handler()

                if self.state == CommTaskState.IDLE:
                    # Do nothing. Wait for user/GUI to change this state
                    self.update.wait()

                elif self.state == CommTaskState.SYNC:

                    received_frame = self.__sync_loop()
                    if received_frame is None:
                        print(">> SYNC failed")
                        # Return to IDLE
                        self._set_state(CommTaskState.IDLE)
                        #  Update GUI
                        if self.connman_gui is not None:
                            self.connman_gui.place_order(
                                ConnManOrder.STATUS_FAILED
                            )
                        continue

                    # Configure channels
                    for i in range(received_frame.n_of_channels):
                        self.data_registry.add_channel(ch_id=i)

                    # Send Acknowledge
                    ack_frame = serialize_frame(frame_type="ack")
                    self.serial_ctrl.send(ack_frame)

                    # Switch to connected
                    self._set_state(CommTaskState.CONNECTED)

                    #  Update GUI
                    if self.connman_gui is not None:
                        self.connman_gui.ch_info_gui.place_channel_info()

                        self.connman_gui.place_order(
                            ConnManOrder.STATUS_CONNECTED,
                            received_frame.n_of_channels
                        )

                elif self.state == CommTaskState.CONNECTED:
                    # TODO: keep connection alive through PING
                    # Do nothing. Wait for user prompt on GUI (Start Button)
                    self.update.wait()

                    # Send message to MCU
                    # Switch state to transfer

                elif self.state == CommTaskState.TRANSFER:
                    # Poll for message
                    response = self.serial_ctrl.listen_msg(b"$%&")
                    if response is None:
                        continue

                    # Parse data
                    try:
                        received_frame = MCTPFrame()
                        received_frame.parse(response)
                        # print(received_frame)
                    except MCTPParseError as exc:
                        print(exc)
                        continue
                    except UnicodeDecodeError as exc:
                        print(exc)
                        continue

                    if received_frame.frame_type == "data":
                        # GUI
                        if self.connman_gui is not None:
                            # List channels received to update channel info.
                            updated_channels = list(
                                received_frame.data_channels.keys()
                            )
                            updated_channels += list(
                                received_frame.text_channels.keys()
                            )
                            # Update channel info.
                            self.connman_gui.ch_info_gui.update_info(
                                updated_channels
                            )
                            # Display any received text.
                            self.connman_gui.place_order(
                                ConnManOrder.APPEND_TEXT,
                                received_frame.text_channels
                            )
                            # Display info.
                            self.connman_gui.place_order(
                                ConnManOrder.CH_INFO_DRAW
                            )

                        # Append data to data registry.
                        self.data_registry.append_data(
                            received_frame.data_channels)
                        self.data_registry.append_text(
                            received_frame.text_channels)

                        self.frames_received += 1
                        self.bytes_received += received_frame.data_size
                        self.__print_transfer()

    def __stop_loop(self):
        """
        Send stop frames until a confirmation is received.
        """
        stop_frame = serialize_frame(frame_type="stop")
        self.serial_ctrl.send(stop_frame)
        received_frame = MCTPFrame()

        # Send STOP frames until a stop confirmation arrives
        # or it timeouts.
        self.timeouts.set_timeout("stop", 2)
        while received_frame.frame_type != "stop":
            if self.timeouts.check_timeout("stop"):
                print("STOP confirmation timeout. Dropping connection")
                self._set_state(CommTaskState.IDLE)
                return

            try:
                self.serial_ctrl.send(stop_frame)
                response = self.serial_ctrl.listen_msg(delimiter=b"$%&")
                if response is not None:
                    received_frame.parse(response)
            except SerialCtrlError as exc:
                print(exc)
                # TODO: raise
                self.stop()
                return
            except MCTPParseError as exc:
                print(exc)
                continue

        self._set_state(CommTaskState.CONNECTED)

    def __drop_loop(self):
        """
        Send drop frames until a confirmation is received.
        """
        drop_frame = serialize_frame(frame_type="drop")
        self.serial_ctrl.send(drop_frame)
        received_frame = MCTPFrame()

        self.timeouts.set_timeout("drop", 3)
        while received_frame.frame_type != "drop":
            if self.timeouts.check_timeout("drop"):
                print("Warning: DROP confirmation timeout. \
Restart performer if future connection attempts fails")
                self._set_state(CommTaskState.IDLE)
                return

            try:
                self.serial_ctrl.send(drop_frame)
                response = self.serial_ctrl.listen_msg(delimiter=b"$%&")
                print(response)
                if response is not None:
                    received_frame.parse(response)
            except SerialCtrlError as exc:
                print(exc)
                # TODO: raise
                self.stop()
                return
            except MCTPParseError as exc:
                print(exc)
                continue

        self._set_state(CommTaskState.IDLE)

    def __sync_loop(self):
        """
        Send sync frames until a confirmation arrives.
        """
        sync_frame = serialize_frame(frame_type="sync")
        received_frame = MCTPFrame()

        self.timeouts.set_timeout("sync", 5)
        while received_frame.frame_type != "sync_resp":
            if self.timeouts.check_timeout("sync"):
                print("SYNC confirmation timeout. Dropping connection")
                self._set_state(CommTaskState.IDLE)
                return None

            try:
                self.serial_ctrl.send(sync_frame)
                response = self.serial_ctrl.listen_msg(delimiter=b"$%&")
                if response is not None:
                    received_frame.parse(response)
            except SerialCtrlError as exc:
                print(exc)
                self.stop()
                # TODO: raise
                return None
            except MCTPParseError as exc:
                print(exc)
                continue
            except UnicodeDecodeError:
                # TODO: Put in parser. Error when decoding utf-8.
                continue

        return received_frame

    def _set_state(self, new_state):
        """
        Change communication task state and notify thread.

        Args:
            new_state (CommTaskState): New state to be set.

        Returns:
            None: Returns nothing.
        """
        with self.update:
            print(f"{self.state} >> {new_state}")
            self.state = new_state
            # Wake up the thread waiting on this condition
            self.update.notify()
            self._print_state(new_state)

    @staticmethod
    def _print_state(state):
        """
        Print state on terminal with appropriate color.

        Args:
            state (CommTaskState): State name to print.

        Returns:
            None: Returns nothing.
        """
        color = 34
        match state:
            case CommTaskState.IDLE:
                color = 34
            case CommTaskState.SYNC:
                color = 33
            case CommTaskState.CONNECTED:
                color = 31
            case CommTaskState.TRANSFER:
                color = 92

        print(f"\033[{color}m[{state}]\033[0m")

    def __print_transfer(self):
        # Need curses to work or a separate thread + no echo input
        sys.stdout.write(f"\r{self.frames_received} frames | {self.bytes_received} bytes")
        sys.stdout.flush()
