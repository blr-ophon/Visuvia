"""
This module provides the MCTPFrame and MSFPParseError classes, for
parsing bytes into MCTP frames, and the serialize_frame function
to create serialized MCTP frames.

The MCTPFrame has methods to parse raw bytes as MSFP frames. It
stores the parsed data in it's attributes and raises MCTPParseError
if an error occurs during parsing.

The serialize_frame function is used to create serialized MCTP frames
in bytes format.

Usage example:
    import mctp

    # Creating channel data
    channels = []
    channel1 = [DataType.INT8, [1, 2, 3, 4]]
    channel2 = [DataType.INT8, [5, 6, 7, 8]]
    channel3 = [DataType.FLOAT32, [1.1, 2.2, 3.3]]
    channels.append(channel1)
    channels.append(channel2)
    channels.append(channel3)

    # Creating data frame
    data_frame = serialize_frame(frame_type="data", channels)

    # Parsing a frame
    try:
        parsed_data_frame = MCTPFrame()
        parsed_data_frame.parse(data_frame)
    except MCTPParseError as exc:
        print(exc)
"""


# Standard library imports
from enum import Enum
import struct


__all__ = ["MCTPFrame", "MCTPParseError", "serialize_frame"]


# Struct unpacking
HEADER_FORMAT = '<BH5B'
DATAINFO_FORMAT = '<BHB'
# MCTP specification
EOM = b'\x24\x25\x26'
EOM_SIZE = 3
HEADER_SIZE = 8
DATAINFO_SIZE = 4
MIN_FRAME_SIZE = HEADER_SIZE + EOM_SIZE
MAX_CHANNELS = 32


class ParserErrorCode(Enum):
    """
    Enum for parsing error codes.
    """
    ELESSMIN = 0         # Packet smaller than minimun size
    EUNMATCHSIZE = 1     # header data size not matching data section size
    EBADTYPE = 2         # Unknown frame type specifier
    EBADDATATYPE = 3     # Unknown data type specifier
    EBADDATA = 4         # Datainfo does not describe data accurately
    ECHEXCEED = 5        # More than 32 channels specified


class FrameType(Enum):
    """
    Enum for the MCTP frame type identifiers.
    Values from MCTP specification.
    """
    NONE = 0
    SYNC = 1
    SYNC_RESP = 2
    ACK = 3
    REQUEST = 4
    DATA = 5
    STOP = 6
    DROP = 7


class DataType(Enum):
    """
    Enum for the MCTP data type Identifiers.
    Values from MCTP specification.
    """
    CHAR = 0
    INT8 = 1
    INT16 = 2
    INT32 = 3
    UINT8 = 4
    UINT16 = 5
    UINT32 = 6
    FLOAT8 = 7
    FLOAT16 = 8
    FLOAT32 = 9


class MCTPParseError(Exception):
    """
    Custom exception for parsing errors.

    Args:
        msg (str): String describing exception.
        code (ParserErrorCode): Error Code

    Attributes:
        msg (str): String describing exception.
        code (ParserErrorCode): Error Code
    """
    def __init__(self, msg, code):
        self.code = code
        self.message = f"{msg}: {code.name}"
        super().__init__(self.message)

    def __str__(self):
        return self.message


class MCTPFrame():
    """
    Parses bytes into MCTP frames from raw message. Stores the parsed
    data to attributes and raises MCTPParseError if an error occurs.
    The data_channels and n_of_channels fields are only relevant to DATA
    and SYNC_RESP frames.

    Attributes:
        frame_type (str): Frame type.
        __frame_type_enum (FrameType): MCTP identifer for frame type.
        data_size (int): Size of data section.
        data_channels (dict[int, list]): Keys are channels and values
            are plot data received from them.
        text_channels (dict[int, list]): Keys are channels and values
            are text data received from them.
        n_of_channels: Number of channels.

    Public Methods:
        parse: Parse bytes.

    Internal Methods:
        _parse_data: Convert bytes data into a list of values based on
            specified data type.
    """
    def __init__(self):
        self.frame_type = None
        self.__frame_type_enum = FrameType.NONE
        self.data_size = 0
        self.data_channels: dict[int, list] = {}
        self.text_channels: dict[int, str] = {}
        self.n_of_channels = 0

    def __str__(self):
        mctp_frame_str = f"| {self.frame_type} | Data size: {self.data_size} | "
        match self.__frame_type_enum:
            case FrameType.SYNC_RESP:
                mctp_frame_str += f"Channels:{self.n_of_channels} | "
            case FrameType.DATA:
                mctp_frame_str += f"Channels:{self.n_of_channels} | "
                # DEBUG:
                # mctp_frame_str += self.data_channels.__str__()
        return mctp_frame_str

    def parse(self, raw_msg):
        """
        Parse MCTP frame.

        Parameters:
            raw_msg (bytes): The message to be parsed in bytes format.

        Returns:
            None: Returns nothing.

        Raises:
            MCTPParseError: If the parsing failed.
        """
        self.text_channels = {}
        self.data_channels = {}

        if len(raw_msg) < MIN_FRAME_SIZE:
            print(raw_msg)
            raise MCTPParseError("Error while parsing",
                                 ParserErrorCode.ELESSMIN)

        # Divide into Header and Data sections
        mctp_header = raw_msg[:8]
        type_identifier, self.data_size, *_ = struct.unpack(
            HEADER_FORMAT, mctp_header
        )
        try:
            self.__frame_type_enum = FrameType(type_identifier)
            self.frame_type = self.__frame_type_enum.name.lower()
        except ValueError as exc:
            raise MCTPParseError("Error while parsing header",
                                 ParserErrorCode.EBADTYPE) from exc

        mctp_data = raw_msg[HEADER_SIZE:HEADER_SIZE + self.data_size]

        # Process data
        total_data_read = 0
        match self.__frame_type_enum:
            case FrameType.SYNC_RESP:
                # Get number of channels
                self.n_of_channels = struct.unpack('<B', mctp_data[0:1])[0]
                if self.n_of_channels > MAX_CHANNELS:
                    raise MCTPParseError("Error while parsing data",
                                         ParserErrorCode.ECHEXCEED)
                total_data_read += 1

            case FrameType.DATA:
                # Get number of channels
                self.n_of_channels = struct.unpack('<B', mctp_data[0:1])[0]
                if self.n_of_channels > MAX_CHANNELS:
                    raise MCTPParseError("Error while parsing data",
                                         ParserErrorCode.ECHEXCEED)
                total_data_read += 1

                datainfo_beg = 1
                datainfo_end = datainfo_beg + DATAINFO_SIZE
                while total_data_read < self.data_size:

                    # Get data info
                    try:
                        ch_id, ch_data_size, ch_datatype_identifier = struct.unpack(
                            DATAINFO_FORMAT,
                            mctp_data[datainfo_beg:datainfo_end])
                    except struct.error as exc:
                        raise MCTPParseError("Error while parsing data",
                                             ParserErrorCode.EBADDATA) from exc

                    # Check if data matches header before attempting to
                    # parse channeldata
                    total_data_read += DATAINFO_SIZE + ch_data_size
                    if total_data_read > self.data_size:
                        raise MCTPParseError("Error while parsing data",
                                             ParserErrorCode.EUNMATCHSIZE)

                    # Convert and get data
                    ch_raw_data = mctp_data[datainfo_end:datainfo_end+ch_data_size]
                    try:
                        parsed_data = self._convert_data(
                            ch_raw_data,
                            ch_datatype_identifier
                        )
                    except MCTPParseError as exc:
                        raise MCTPParseError("Error while parsing data",
                                             ParserErrorCode.EBADDATA) from exc

                    if DataType(ch_datatype_identifier) == DataType.CHAR:
                        self.text_channels[ch_id] = parsed_data[0].decode("utf-8")
                    else:
                        self.data_channels[ch_id] = parsed_data

                    # Update for next channel
                    datainfo_beg += ch_data_size + DATAINFO_SIZE
                    datainfo_end += ch_data_size + DATAINFO_SIZE

    def _convert_data(self, raw_data, datatype_identifier):
        """
        Convert byte stream to list of data with specified data type

        Parameters:
            raw_data (bytes): The data bytes to be converted.
            datatype_identifier (int): The identifier according to MCTP
            specification.

        Returns:
            list[]: Array of values based on the provided identifier.

        Raises:
            MCTPParseError: If the failed.
        """
        try:
            data_type = DataType(datatype_identifier)
        except ValueError as exc:
            raise MCTPParseError("Error while converting data",
                                 ParserErrorCode.EBADDATATYPE) from exc

        format_code, var_size = _parse_datatype(data_type)

        n_of_samples = int(len(raw_data) / var_size)
        format_string = f"<{n_of_samples}{format_code}"

        try:
            converted_data = struct.unpack(format_string, raw_data)
        except struct.error as exc:
            raise MCTPParseError("Error while converting data",
                                 ParserErrorCode.EBADDATATYPE) from exc

        return converted_data


def _string_to_frame_type(frame_type_str):
    """ Convert string to MCTP frame type identifer."""
    output = ""
    match frame_type_str:
        case "unknown":
            output = FrameType.NONE
        case "sync":
            output = FrameType.SYNC
        case "sync_resp":
            output = FrameType.SYNC_RESP
        case "ack":
            output = FrameType.ACK
        case "request":
            output = FrameType.REQUEST
        case "data":
            output = FrameType.DATA
        case "stop":
            output = FrameType.STOP
        case "drop":
            output = FrameType.DROP
    return output


def _parse_datatype(data_type):
    """
    Get 'struct' format code from MCTP data_type. Also gets the variable
    size in bytes for the data type.

    Parameters:
        data_type (DataType): The data type identifier.

    Returns:
        str: The format code for 'struct'.
        int: The size in bytes for the type.
    """
    format_code = None
    var_size = None
    match data_type:
        case DataType.CHAR:
            format_code = 's'
            var_size = 1
        case DataType.INT8:
            format_code = 'b'
            var_size = 1
        case DataType.INT16:
            format_code = 'h'
            var_size = 2
        case DataType.INT32:
            format_code = 'i'
            var_size = 4
        case DataType.UINT8:
            format_code = 'B'
            var_size = 1
        case DataType.UINT16:
            format_code = 'H'
            var_size = 2
        case DataType.UINT32:
            format_code = 'I'
            var_size = 4
        case DataType.FLOAT8:
            # TODO
            format_code = 'B'
            var_size = 1
        case DataType.FLOAT16:
            # TODO
            format_code = 'H'
            var_size = 2
        case DataType.FLOAT32:
            format_code = 'f'
            var_size = 4
        case _:
            pass

    return format_code, var_size


def serialize_frame(frame_type, data_channels=None):
    # TODO: Use dict of np.arrays for channels.
    """
    Creates serialized frame in bytes based on specified type. If data is
    provided, it will be appended in order to channels in crescent order.
    e.g: 1st element goes to channel 1.

    Parameters:
        frame_type (str): Frame type string.
        data_channels (list[DataType, list[]]): List of 2D lists, where the
        first element is the data type and the second is the list of values.

    Returns:
        bytes: The serialized frame.
    """
    # Data
    data_size = 0
    mctp_data = b''
    frame_type_enum = _string_to_frame_type(frame_type)
    match frame_type_enum:
        case FrameType.SYNC_RESP:
            if data_channels is None:
                return None
            n_of_channels = len(data_channels)
            mctp_data += n_of_channels.to_bytes(1, byteorder="little")
            data_size += 1
        case FrameType.DATA:
            if data_channels is None:
                return None
            n_of_channels = len(data_channels)
            mctp_data += n_of_channels.to_bytes(1, byteorder="little")
            data_size += 1

            ch_id = 0
            for ch_datatype, ch_data in data_channels:
                ch_data_serialized = serialize_channel_data(ch_datatype,
                                                            ch_data)
                # Datainfo (channel id + channel size + channel data type)
                mctp_data += ch_id.to_bytes(1, byteorder="little")
                ch_id += 1
                mctp_data += (len(ch_data_serialized)).to_bytes(
                    2, byteorder="little")
                mctp_data += (ch_datatype.value).to_bytes(
                    1, byteorder="little")
                # Channel Data
                mctp_data += ch_data_serialized

                data_size += DATAINFO_SIZE + len(ch_data_serialized)

    # Header
    mctp_header = (frame_type_enum.value).to_bytes(1, byteorder='little')
    mctp_header += data_size.to_bytes(2, byteorder='little')
    mctp_header += b'\x05\x05\x05\x05\x05'

    # Concatenate header, data and EOM
    frame = mctp_header + mctp_data + EOM
    return frame


def serialize_channel_data(data_type, data):
    """
    Convert list of values to serialized bytes based on specified type.

    Parameters:
        data_type (DataType): Type of data.
        data (list[]): List of values to convert to bytes.

    Returns:
        bytes: The serialized data.
    """
    format_code, *_ = _parse_datatype(data_type)

    bytestream = b''
    for sample in data:
        bytestream += struct.pack(f"<{format_code}", sample)

    return bytestream


if __name__ == "__main__":
    channels = []
    channel1 = [DataType.INT8, [1, 2, 3, 4]]
    channel2 = [DataType.INT8, [5, 6, 7, 8]]
    channel3 = [DataType.FLOAT32, [1.1, 2.2, 3.3]]
    channels.append(channel1)
    channels.append(channel2)
    channels.append(channel3)

    TEST_FLOAT = 1.1
    test_stream = struct.pack("<f", TEST_FLOAT)
    print(test_stream)
    print([hex(b) for b in test_stream])

    data_frame = serialize_frame(FrameType.DATA, channels)
    print(data_frame)
    parsed_data_frame = MCTPFrame()
    parsed_data_frame.parse(data_frame)
    print(parsed_data_frame)
