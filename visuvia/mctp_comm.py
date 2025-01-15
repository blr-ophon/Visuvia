"""
This module provides the CommTask class.

The CommTask implements the MCTP controller side finite state machine,
which handles MCTP connection between performer and controller. It
works independently as a thread and contains methods to start and
stop the thread, as well as methods for user-triggered events of the
finite state machine.
"""


# Standard library imports
import time
import threading
from enum import Enum
# Local imports
from visuvia.utils.mctp import MCTPFrame, MCTPParseError, serialize_frame
from visuvia.gui.orders import ConnManOrder


__all__ = ["CommTask", "CommTaskState"]


class CommTaskState(Enum):
    """
    Identifier for the state of the communication task finite state machine
    """
    IDLE = 1
    SYNC = 2
    CONNECTED = 3
    LISTENING = 4

    def __str__(self):
        return self.name


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
        flag_send_req (bool):
        flag_send_stop (bool):
        flag_send_drop (bool):
    """
    def __init__(self, serial_ctrl, data_registry, connman_gui=None):
        self.state = CommTaskState.IDLE
        self.serial_ctrl = serial_ctrl
        self.data_registry = data_registry
        self.connman_gui = connman_gui

        self.thread = None
        self.update = threading.Condition()
        self.running = False

        # Set flags for the main thread to execute actions.
        # All serial communication must happen inside commtask thread.
        self.flag_send_req = False
        self.flag_send_stop = False
        self.flag_send_drop = False

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
        self.running = False
        self._set_state(CommTaskState.IDLE)
        self.thread.join()
        self.send_drop()

    def start_sync(self):
        """
        Switch from IDLE to SYNC state.

        Returns:
            None: Returns nothing.
        """
        if self.connman_gui is not None:
            self.connman_gui.enqueue_update(ConnManOrder.STATUS_SYNCING)
        if self.state == CommTaskState.IDLE:
            self._set_state(CommTaskState.SYNC)

    def send_request(self):
        """
        Switch from CONNECTED to LISTENING state. Sends REQUEST frame.

        Returns:
            None: Returns nothing.
        """
        if self.state != CommTaskState.CONNECTED:
            return

        self._set_state(CommTaskState.LISTENING)

        with self.update:
            self.flag_send_req = True
            self.update.notify()

    def send_stop(self):
        """
        Send STOP frame. Only works if task is in listening state.

        Returns:
            None: Returns nothing.
        """
        if self.state != CommTaskState.LISTENING:
            return

        with self.update:
            self.flag_send_stop = True
            self.update.notify()

    def send_drop(self):
        """
        Send DROP frame.

        Returns:
            None: Returns nothing.
        """
        self.flag_send_drop = True
        self._set_state(CommTaskState.IDLE)

    def __application_event_handler(self):
        """
        Check for application-trigerred events.

        Returns:
            None: Returns nothing.
        """
        # Drop has highest priority.
        if self.flag_send_drop:
            drop_frame = serialize_frame(frame_type="drop")
            self.serial_ctrl.send(drop_frame)
            self.flag_send_drop = False

        elif self.flag_send_req:
            req_frame = serialize_frame(frame_type="request")
            self.serial_ctrl.send(req_frame)
            self.flag_send_req = False

            # Initialize time reference for plotting.
            # This disconsiders the time for the request frame to arrive and
            # the time for MCU to start sending data after being notified.
            # FIXME: Use a dummy RDY packet to set reference for plot.
            self.data_registry.set_time_ref()

        elif self.flag_send_stop:
            stop_frame = serialize_frame(frame_type="stop")
            self.serial_ctrl.send(stop_frame)
            self.flag_send_stop = False

    def __run(self):
        """
        Communication task thread. Implements the MCTP controller side finite
        state machine

        Returns:
            None: Returns nothing.
        """
        sync_timeout_start = False
        sync_timeout_start_time = 0

        while self.running:
            with self.update:

                self.__application_event_handler()

                if self.state == CommTaskState.IDLE:
                    # Do nothing. Wait for user/GUI to change this state
                    self.update.wait()

                elif self.state == CommTaskState.SYNC:

                    # Send sync frame
                    sync_frame = serialize_frame(frame_type="sync")
                    self.serial_ctrl.send(sync_frame)

                    # Poll for response
                    response = self.serial_ctrl.listen_msg(b"$%&")

                    # Always check if fsm has not been stopped during blocking
                    # operation after it is done
                    if not self.running:
                        continue

                    # Parse and validate response
                    if response is None:
                        continue

                    try:
                        received_frame = MCTPFrame()
                        received_frame.parse(response)
                    except MCTPParseError as exc:
                        print(exc)
                        continue
                    except UnicodeDecodeError:
                        # TODO: Put in parser. Error when decoding utf-8.
                        continue

                    if received_frame.frame_type == "sync_resp":
                        # Configure channels
                        for i in range(received_frame.n_of_channels):
                            self.data_registry.add_channel(ch_id=i)

                        # Send Acknowledge
                        ack_frame = serialize_frame(frame_type="ack")
                        self.serial_ctrl.send(ack_frame)
                        # self.serial_ctrl.send(ack_frame)

                        # Switch to connected
                        self._set_state(CommTaskState.CONNECTED)

                        #  Update GUI
                        if self.connman_gui is not None:
                            self.connman_gui.ch_info_gui.place_channel_info()

                            self.connman_gui.enqueue_update(
                                ConnManOrder.STATUS_CONNECTED,
                                received_frame.n_of_channels
                            )

                    else:
                        # TODO: improper, this does not handle the MCU not sending anything
                        # Try syncing until timeout
                        if not sync_timeout_start:
                            sync_timeout_start = True
                            sync_timeout_start_time = time.time()

                        if time.time() - sync_timeout_start_time > 3:
                            sync_timeout_start = False
                            print(">> SYNC failed")
                            # Return to IDLE
                            self._set_state(CommTaskState.IDLE)
                            #  Update GUI
                            if self.connman_gui is not None:
                                self.connman_gui.enqueue_update(
                                    ConnManOrder.STATUS_FAILED
                                )

                elif self.state == CommTaskState.CONNECTED:
                    # TODO: keep connection alive through PING
                    # Do nothing. Wait for user prompt on GUI (Start Button)
                    self.update.wait()

                    # Send message to MCU
                    # Switch state to listening

                elif self.state == CommTaskState.LISTENING:
                    # Poll for message
                    response = self.serial_ctrl.listen_msg(b"$%&")
                    # print(response)
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

                    if received_frame.frame_type == "stop":
                        self._set_state(CommTaskState.CONNECTED)
                    elif received_frame.frame_type == "data":
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
                            self.connman_gui.enqueue_update(
                                ConnManOrder.APPEND_TEXT,
                                received_frame.text_channels
                            )
                            # Display info.
                            self.connman_gui.enqueue_update(
                                ConnManOrder.CH_INFO_DRAW
                            )

                        # Append data to data registry.
                        self.data_registry.append_data(
                            received_frame.data_channels)
                        self.data_registry.append_text(
                            received_frame.text_channels)

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
            case CommTaskState.LISTENING:
                color = 92

        print(f"\033[{color}m[{state}]\033[0m")
