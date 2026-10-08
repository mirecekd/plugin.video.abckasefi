# resources/lib/qr_tables.py
"""Static QR tables for error-correction level M, versions 1-10 (ISO/IEC 18004)."""
from __future__ import annotations

MAX_VERSION = 10

# version -> (EC codewords per block, [(block count, data codewords per block), ...]); blocks in ascending size.
BLOCKS_M: dict[int, tuple[int, list[tuple[int, int]]]] = {
    1: (10, [(1, 16)]),
    2: (16, [(1, 28)]),
    3: (26, [(1, 44)]),
    4: (18, [(2, 32)]),
    5: (24, [(2, 43)]),
    6: (16, [(4, 27)]),
    7: (18, [(4, 31)]),
    8: (22, [(2, 38), (2, 39)]),
    9: (22, [(3, 36), (2, 37)]),
    10: (26, [(4, 43), (1, 44)]),
}

# version -> centre coordinates of the alignment patterns (rows and columns)
ALIGNMENT_CENTERS: dict[int, list[int]] = {
    1: [],
    2: [6, 18],
    3: [6, 22],
    4: [6, 26],
    5: [6, 30],
    6: [6, 34],
    7: [6, 22, 38],
    8: [6, 24, 42],
    9: [6, 26, 46],
    10: [6, 28, 50],
}

PAD_BYTES = (0xEC, 0x11)
FORMAT_GENERATOR = 0x537
FORMAT_MASK = 0x5412
VERSION_GENERATOR = 0x1F25


def data_capacity(version: int) -> int:
    """Number of data codewords of `version` at level M."""
    return sum(count * size for count, size in BLOCKS_M[version][1])


def char_count_bits(version: int) -> int:
    """Width of the byte-mode character count field."""
    return 8 if version < 10 else 16
