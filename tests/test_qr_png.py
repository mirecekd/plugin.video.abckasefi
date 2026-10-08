# tests/test_qr_png.py
"""resources/lib/png.py: PNG signature, chunks, CRCs, scanline layout and pixel values of a rendered QR matrix."""
import struct
import zlib

import pytest

from resources.lib import png, qr

URL = "http://192.168.1.20:43211/Xk3_9aB-c2D4eF6gH8iJkQ"


def read_chunks(data):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos, chunks = 8, []
    while pos < len(data):
        length, kind = struct.unpack(">I4s", data[pos:pos + 8])
        body = data[pos + 8:pos + 8 + length]
        (crc,) = struct.unpack(">I", data[pos + 8 + length:pos + 12 + length])
        assert crc == zlib.crc32(kind + body) & 0xFFFFFFFF
        chunks.append((kind, body))
        pos += 12 + length
    assert pos == len(data)
    return chunks


def test_png_structure_signature_ihdr_idat_iend_and_crcs():
    matrix = qr.encode(URL)
    chunks = read_chunks(png.to_png(matrix, scale=5, border=3))
    assert [k for k, _ in chunks] == [b"IHDR", b"IDAT", b"IEND"]
    side = (len(matrix) + 6) * 5
    assert struct.unpack(">IIBBBBB", chunks[0][1]) == (side, side, 8, 0, 0, 0, 0)
    assert chunks[2][1] == b""
    raw = zlib.decompress(chunks[1][1])
    assert len(raw) == side * (1 + side)
    assert all(raw[i * (1 + side)] == 0 for i in range(side))  # filter type 0 on every scanline


def test_png_pixels_follow_the_matrix_with_a_white_quiet_zone():
    matrix = qr.encode("abc")
    scale, border = 4, 2
    raw = zlib.decompress(read_chunks(png.to_png(matrix, scale, border))[1][1])
    side = (len(matrix) + 2 * border) * scale
    for y in range(side):
        for x in range(side):
            r, c = y // scale - border, x // scale - border
            inside = 0 <= r < len(matrix) and 0 <= c < len(matrix)
            assert raw[y * (1 + side) + 1 + x] == (0 if inside and matrix[r][c] else 255)


def test_png_default_scale_and_border_and_argument_validation():
    matrix = qr.encode("a")
    chunks = read_chunks(png.to_png(matrix))
    assert struct.unpack(">II", chunks[0][1][:8]) == ((21 + 8) * 10, (21 + 8) * 10)
    with pytest.raises(ValueError):
        png.to_png(matrix, scale=0)
    with pytest.raises(ValueError):
        png.to_png([[True, False]])
