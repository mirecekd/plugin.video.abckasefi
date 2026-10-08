# resources/lib/png.py
"""Minimal 8-bit greyscale PNG writer (struct + zlib only) for QR module matrices."""
import struct
import zlib

PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


def _chunk(kind, data):
    crc = zlib.crc32(kind + data) & 0xFFFFFFFF
    return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)


def to_png(matrix, scale=10, border=4):
    """Render `matrix` (rows of bools, True = dark) as black-on-white PNG bytes with a `border`-module quiet zone."""
    if scale < 1 or border < 0:
        raise ValueError("scale must be >= 1 and border >= 0")
    side = len(matrix) + 2 * border
    pad = b"\xff" * (border * scale)
    body = []
    for row in matrix:
        if len(row) != len(matrix):
            raise ValueError("matrix must be square")
        line = b"\x00" + pad + b"".join((b"\x00" if dark else b"\xff") * scale for dark in row) + pad
        body.extend([line] * scale)
    blank = b"\x00" + b"\xff" * (side * scale)
    raw = b"".join([blank] * (border * scale) + body + [blank] * (border * scale))
    size = side * scale
    ihdr = struct.pack(">IIBBBBB", size, size, 8, 0, 0, 0, 0)
    return PNG_SIGNATURE + _chunk(b"IHDR", ihdr) + _chunk(b"IDAT", zlib.compress(raw, 9)) + _chunk(b"IEND", b"")
