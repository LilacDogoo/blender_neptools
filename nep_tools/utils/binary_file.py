from io import BufferedReader
from struct import Struct

# DEFINE STRUCTURES
from typing import BinaryIO

struct_ULongL = Struct('<L')  # Unsigned Long - Little Endian
struct_ULongB = Struct('>L')  # Unsigned Long - Big Endian
struct_SLongL = Struct('<l')  # Signed Long - Little Endian
struct_SLongB = Struct('>l')  # Signed Long - Big Endian
struct_UShortL = Struct('<H')  # Unsigned Short - Little Endian
struct_UShortB = Struct('>H')  # Unsigned Short - Big Endian
struct_floatL = Struct('<f')  # Float - Little Endian
struct_floatB = Struct('>f')  # Float - Big Endian
struct_halfFloatL = Struct('<e')  # Half Float - Little Endian
struct_halfFloatB = Struct('>e')  # Half Float - Big Endian


def read_byte_unsigned(stream: BinaryIO):
    return stream.read(1)[0]


def read_byte_signed(stream: BinaryIO):
    return stream.read(1)[0]


def read_byte_as_float(stream: BinaryIO):
    return float(stream.read(1)[0]) / 255.0


def read_string(stream: BinaryIO):
    B = bytearray()
    b = stream.read(1)[0]
    while b != 0:
        B.append(b)
        b = stream.read(1)[0]
    return B.decode('utf8', 'replace')


def read_long_unsigned_little_endian(stream: BinaryIO):
    return struct_ULongL.unpack_from(stream.read(4))[0]


def read_long_signed_little_endian(stream: BinaryIO):
    return struct_SLongL.unpack_from(stream.read(4))[0]


def read_short_unsigned_little_endian(stream: BinaryIO):
    return struct_UShortL.unpack_from(stream.read(2))[0]


def read_float_little_endian(stream: BinaryIO):
    return struct_floatL.unpack_from(stream.read(4))[0]


def read_half_float_little_endian(stream: BinaryIO):
    return struct_halfFloatL.unpack_from(stream.read(2))[0]


def read_long_unsigned_big_endian(stream: BinaryIO):
    return struct_ULongB.unpack_from(stream.read(4))[0]


def read_long_signed_big_endian(stream: BinaryIO):
    return struct_SLongB.unpack_from(stream.read(4))[0]


def read_short_unsigned_big_endian(stream: BinaryIO):
    return struct_UShortB.unpack_from(stream.read(2))[0]


def read_float_big_endian(stream: BinaryIO):
    return struct_floatB.unpack_from(stream.read(4))[0]


def read_half_float_big_endian(stream: BinaryIO):
    return struct_halfFloatB.unpack_from(stream.read(2))[0]


class LD_BinaryReader:
    def __init__(self, stream: BinaryIO, big_endian: bool) -> None:
        super().__init__()

        self.stream = stream
        self.read_byte_unsigned = lambda: read_byte_unsigned(self.stream)
        self.read_byte_signed = lambda: read_byte_signed(self.stream)
        self.read_byte_as_float = lambda: read_byte_as_float(self.stream)
        self.read_string = lambda: read_string(self.stream)
        # TODO test if endian of 'float' ever changes
        if big_endian:
            self.read_long_unsigned = lambda: read_long_unsigned_big_endian(self.stream)
            self.read_long_signed = lambda: read_long_signed_big_endian(self.stream)
            self.read_short_unsigned = lambda: read_short_unsigned_big_endian(self.stream)
            self.read_float = lambda: read_float_big_endian(self.stream)
            self.read_half_float = lambda: read_half_float_big_endian(self.stream)
        else:
            self.read_long_unsigned = lambda: read_long_unsigned_little_endian(self.stream)
            self.read_long_signed = lambda: read_long_signed_little_endian(self.stream)
            self.read_short_unsigned = lambda: read_short_unsigned_little_endian(self.stream)
            self.read_float = lambda: read_float_little_endian(self.stream)
            self.read_half_float = lambda: read_half_float_little_endian(self.stream)

    def seek(self, amount: int):
        self.stream.seek(amount, 1)

    def goto(self, location: int):
        self.stream.seek(location)

    def close(self):
        self.stream.close()
