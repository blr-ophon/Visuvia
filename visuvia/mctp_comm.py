"""
This module provides the CommTask object.

The CommTask implements the MCTP finite state machine for controller,
which handles MCTP connection between performer and controller. It
works independently as a thread and contains methods to start and
stop the thread, as well as methods for user-triggered events of the
finite state machine.

The GUI interacts with the communication task by calling it's methods
according to user input, such as requesting data after a button is pressed.
The communication task interacts with the GUI by calling GUI methods based
on it's internal events, such as displaying available channels after the .
end of sync phase.
"""


# Standard library imports
import time
import threading
from enum import Enum
# Local imports
from visuvia.utils.mctp import MCTPFrame, MCTPParseError, serialize_frame
from visuvia.gui.orders import ConnManOrder


__all__ = ["CommTask"]


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

    Attributes:
        state (CommTaskState):
        serial_ctrl (SerialCtrl):
        data_registry (DataRegistry):
        connman_gui (ConnManagerGUI):
        thread (threading.Thread):
        change_state (threading.Condition()):
        running (bool):

    Public Methods:
        start: Start CommTask thread.
        stop: Stop CommTask thread.
        start_sync: Start SYNC phase.
        send_request: Start requesting data.
        send_stop: Stop data transfer.
        send_drop: Drop connection.

    Private Methods:
        __run: CommTask thread target.
        __set_state: Set CommTask state.
        __print_state: Print CommTask state.
    """
    def __init__(self, serial_ctrl, data_registry, connman_gui=None):
        self.state = CommTaskState.IDLE
        self.serial_ctrl = serial_ctrl
        self.data_registry = data_registry
        self.connman_gui = connman_gui

        self.thread = None
        self.change_state = threading.Condition()
        self.running = False

        # USER ACTIONS
        # All data transfer must happen inside commtask thread
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
        self.__set_state(CommTaskState.IDLE)
        self.thread = threading.Thread(target=self.__run, daemon=True)
        self.thread.start()

    def stop(self):
        """
        Stop communication task thread

        Returns:
            None: Returns nothing.
        """
        self.running = False
        self.__set_state(CommTaskState.IDLE)
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
            self.__set_state(CommTaskState.SYNC)

    def send_request(self):
        """
        Switch from CONNECTED to LISTENING state. Sends REQUEST frame.

        Returns:
            None: Returns nothing.
        """
        # Check current state
        if self.state != CommTaskState.CONNECTED:
            return

        # Set state to listening
        self.__set_state(CommTaskState.LISTENING)

        # Send REQUEST frame
        req_frame = serialize_frame(frame_type="request")
        self.serial_ctrl.send(req_frame)

        # Initialize time reference for plotting. TODO: Use RDY frame
        self.data_registry.set_time_ref()

    def send_stop(self):
        """
        Send STOP frame. Only works if task is in listening state.

        Returns:
            None: Returns nothing.
        """
        # Check current state
        if self.state != CommTaskState.LISTENING:
            return

        # Send STOP frame
        stop_frame = serialize_frame(frame_type="stop")
        self.serial_ctrl.send(stop_frame)

    def send_drop(self):
        """
        Send DROP frame.

        Returns:
            None: Returns nothing.
        """
        drop_frame = serialize_frame(frame_type="drop")
        self.serial_ctrl.send(drop_frame)
        self.__set_state(CommTaskState.IDLE)

    def __run(self):
        """
        Communication task thread. Implements the MCTP controller finite
        state machine

        Returns:
            None: Returns nothing.
        """
        sync_timeout_start = False
        sync_timeout_start_time = 0

        while self.running:
            with self.change_state:

                if self.state == CommTaskState.IDLE:
                    # Do nothing. Wait for user/GUI to change this state
                    self.change_state.wait()

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
                        self.__set_state(CommTaskState.CONNECTED)

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
                            self.__set_state(CommTaskState.IDLE)
                            #  Update GUI
                            if self.connman_gui is not None:
                                self.connman_gui.enqueue_update(
                                    ConnManOrder.STATUS_FAILED
                                )

                elif self.state == CommTaskState.CONNECTED:
                    # TODO: keep connection alive through PING
                    # Do nothing. Wait for user prompt on GUI (Start Button)
                    self.change_state.wait()

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
                        self.__set_state(CommTaskState.CONNECTED)
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

    def __set_state(self, new_state):
        """
        Change communication task state and notify thread.

        Parameters:
            new_state (CommTaskState): New state to be set.

        Returns:
            None: Returns nothing.
        """
        with self.change_state:
            print(f"{self.state} >> {new_state}")
            self.state = new_state
            # Wake up the thread waiting on this condition
            self.change_state.notify()
            self.__print_state(new_state)

    @staticmethod
    def __print_state(state):
        """
        Print state on terminal with appropriate color.

        Parameters:
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
