"""
This module provides the SerialCtrl and SerialCtrlError classes.

The SerialCtrl class handles the opening, closing, and listing of serial
ports. It manages a single serial port at a time and provides methods
to check if the port is open, write, read from it, and close the
connection.

The SerialCtrlError is the exception thrown if an error occurs inside
SerialCtrl methods.

Dependencies:
- pyserial

Usage example:
    from serial_ctrl import SerialCtrl, SerialCtrlError

    serial_ctrl = SerialCtrl()
    port_list = serial_ctrl.get_port_list()
    serial_ctrl.set_serial(port_name=port_list[0], baudrate="9600",
                           timeout=2)
    serial_ctrl.send(b"test\n")
    serial_ctrl.listen_msg(delimiter=b"\n")
    serial_ctrl.close_serial()
"""


# Third party imports
import serial
from serial.tools import list_ports


__all__ = ["SerialCtrl", "SerialCtrlError"]


class SerialCtrlError(Exception):
    """Custom exception for errors related to SerialCtrl."""


class SerialCtrl():
    """
    Manages a serial port connection.

    Attributes:
        serial_port (serial.Serial): The active serial port object.
        port_list (list): List of available serial ports.

    Public Methods:
        set_serial: Set serial_port and open it.
        close_serial: Closes the serial port.
        listen_msg: Read from port until a delimiter.
        send: Write data to port.
        get_port_list: Get list of ports.

    Private Methods:
        __is_valid_port: Filters ports used by UART communication
    """
    def __init__(self):
        self.port_list = []
        self.serial_port: serial.Serial = None

    def set_serial(self, port_name, baudrate, timeout):
        """
        Open serial port with the specified name and baud rate and set as
        serial_port.

        Parameters:
            port_name (str): Name of the serial port (e.g., "/dev/ttyUSB0").
            baudrate (str): Baud rate (e.g, "9600", "115200").

        Returns:
            None: This function does not return anything.

        Raises:
            serial.SerialException: If there is an issue opening the port.
        """
        # Check if port is already open
        if isinstance(self.serial_port, serial.Serial) and \
                self.serial_port.is_open:
            raise SerialCtrlError("Error: Attempting to open busy port.")

        try:
            # Open port by instantiating Serial
            self.serial_port = serial.Serial(
                port=port_name,
                baudrate=baudrate,
                timeout=timeout,)
            print(f"Opened port: {self.serial_port.port} (baud: {self.serial_port.baudrate})")
        except serial.SerialException as exc:
            # Failed opening port
            raise SerialCtrlError(f"Exception occurred while opening the port: {exc}") from exc

    def close_serial(self):
        """
        Close serial_port

        Returns:
            None: This function does not return anything.

        Raises:
            serial.SerialException: If there is an issue closing the port.
        """
        try:
            self.serial_port.close()
        except serial.SerialException as exc:
            raise SerialCtrlError(f"Exception occurred while closing the port: {exc}") from exc

    def listen_msg(self, delimiter):
        """
        Reads from serial_port until the delimiter arrives.

        Parameters:
            delimiter (bytes): The delimiter bytes.

        Returns:
            str: The arriving frame. Returns None if an error occurs.

        Raises:
            serial.SerialException: If there is an issue reading from
            serial_port.
            TypeError: If delimiter is not a (bytes) object.
        """
        try:
            # Read bytes until delimiter or port timeout
            msg = self.serial_port.read_until(delimiter, size=None)
            # DEBUG:
            # if msg:
            #     print(f"      << {msg}")
            return msg
        except TypeError as exc:
            raise SerialCtrlError(f"Error: {exc}") from exc
        except serial.SerialException as exc:
            raise SerialCtrlError(f"Exception occurred while reading from port: {exc}") from exc
        except TimeoutError:
            return None

    def send(self, data):
        """
        Writes data to current port.

        Parameters:
            data (bytes): The data to be sent.

        Returns:
            None: This function does not return anything.

        Raises:
            serial.SerialException: If there is an issue writing to
            serial_port.
        """
        try:
            # DEBUG
            print(f">> {data}")
            self.serial_port.write(data)
        except serial.SerialException as exc:
            raise SerialCtrlError(f"Exception occurred while reading from port: {exc}") from exc

    def get_port_list(self):
        """
        Update port_list and get list of available serial ports in the system.

        Returns:
            List[str]: A list with the names of available serial ports

        Raises:
            serial.SerialException: If there is an issue retrieving list of
            ports.
        """
        try:
            self.port_list = [port.device for port in list_ports.comports()
                              if self.__is_valid_port(port)]
            return self.port_list
        except serial.SerialException as exc:
            raise SerialCtrlError(f"Exception occurred while listing ports: {exc}") from exc

    @staticmethod
    def __is_valid_port(port):
        """
        Check if a port is a valid MCU serial port (USB, UART or ACM).

        Parameters:
            port (ListPortInfo): The port to be checked.

        Returns:
            bool: True for valid port, False for invalid port.

        Raises:
            AttributeError: port is not ListPortInfo.
        """
        try:
            return "USB" in port.description \
                or "UART" in port.description or "ACM" in port.device
        except AttributeError:
            print("Error: Not a ListPortInfo object")
            return False
