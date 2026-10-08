# resources/lib/qr.py
"""Pure-Python QR code encoder: byte mode, error correction level M, versions 1-10.

`encode(text)` returns the module matrix (list of rows of bools, True = dark) WITHOUT the quiet zone.
"""
from __future__ import annotations

from .qr_ecc import format_bits, rs_remainder, version_bits
from .qr_penalty import mask_bit, penalty
from .qr_tables import (
    ALIGNMENT_CENTERS,
    BLOCKS_M,
    MAX_VERSION,
    PAD_BYTES,
    char_count_bits,
    data_capacity,
)


def _data_codewords(payload: bytes, version: int) -> list[int]:
    """Mode indicator, character count, data, terminator and pad codewords for `version`."""
    bits = "0100" + format(len(payload), f"0{char_count_bits(version)}b")
    bits += "".join(format(b, "08b") for b in payload)
    total_bits = data_capacity(version) * 8
    bits += "0" * min(4, total_bits - len(bits))
    bits += "0" * (-len(bits) % 8)
    words = [int(bits[i:i + 8], 2) for i in range(0, len(bits), 8)]
    pad = 0
    while len(words) < data_capacity(version):
        words.append(PAD_BYTES[pad % 2])
        pad += 1
    return words


def _interleave(words: list[int], version: int) -> list[int]:
    """Split into blocks, append Reed-Solomon codewords and interleave data and EC codewords."""
    ec_len, groups = BLOCKS_M[version]
    blocks: list[list[int]] = []
    pos = 0
    for count, size in groups:
        for _ in range(count):
            blocks.append(words[pos:pos + size])
            pos += size
    ecs = [rs_remainder(block, ec_len) for block in blocks]
    out: list[int] = []
    for i in range(max(len(b) for b in blocks)):
        out.extend(b[i] for b in blocks if i < len(b))
    for i in range(ec_len):
        out.extend(e[i] for e in ecs)
    return out


class _Grid:
    """Square module grid plus a parallel map of which modules are function patterns."""

    def __init__(self, version: int) -> None:
        self.size = 17 + 4 * version
        self.mod = [[False] * self.size for _ in range(self.size)]
        self.func = [[False] * self.size for _ in range(self.size)]

    def put(self, row: int, col: int, dark: bool) -> None:
        self.mod[row][col] = dark
        self.func[row][col] = True

    def finder(self, top: int, left: int) -> None:
        """7x7 finder plus its one-module separator; clipped to the grid."""
        for dr in range(-1, 8):
            for dc in range(-1, 8):
                r, c = top + dr, left + dc
                if 0 <= r < self.size and 0 <= c < self.size:
                    inside = 0 <= dr <= 6 and 0 <= dc <= 6
                    self.put(r, c, inside and max(abs(dr - 3), abs(dc - 3)) != 2)

    def alignment(self, cr: int, cc: int) -> None:
        for dr in range(-2, 3):
            for dc in range(-2, 3):
                self.put(cr + dr, cc + dc, max(abs(dr), abs(dc)) != 1)

    def draw_function_patterns(self, version: int) -> None:
        self.finder(0, 0)
        self.finder(0, self.size - 7)
        self.finder(self.size - 7, 0)
        for i in range(8, self.size - 8):
            self.put(6, i, i % 2 == 0)
            self.put(i, 6, i % 2 == 0)
        centers = ALIGNMENT_CENTERS[version]
        last = len(centers) - 1
        for i, cr in enumerate(centers):
            for j, cc in enumerate(centers):
                if (i, j) not in ((0, 0), (0, last), (last, 0)):
                    self.alignment(cr, cc)
        self.draw_format(0)
        if version >= 7:
            self.draw_version(version)
        self.put(self.size - 8, 8, True)  # the always-dark module

    def draw_format(self, mask: int) -> None:
        bits = format_bits(mask)
        n = self.size

        def bit(i: int) -> bool:
            return (bits >> i) & 1 == 1

        for i in range(6):
            self.put(i, 8, bit(i))
        self.put(7, 8, bit(6))
        self.put(8, 8, bit(7))
        self.put(8, 7, bit(8))
        for i in range(9, 15):
            self.put(8, 14 - i, bit(i))
        for i in range(8):
            self.put(8, n - 1 - i, bit(i))
        for i in range(8, 15):
            self.put(n - 15 + i, 8, bit(i))

    def draw_version(self, version: int) -> None:
        bits = version_bits(version)
        for i in range(18):
            dark = (bits >> i) & 1 == 1
            a, b = self.size - 11 + i % 3, i // 3
            self.put(a, b, dark)
            self.put(b, a, dark)

    def place_data(self, codewords: list[int]) -> None:
        """Write the codeword bits in the zigzag order, skipping function modules."""
        bits = [(w >> (7 - k)) & 1 == 1 for w in codewords for k in range(8)]
        idx = 0
        right = self.size - 1
        while right >= 1:
            if right == 6:
                right = 5
            upward = ((right + 1) & 2) == 0
            for vert in range(self.size):
                row = self.size - 1 - vert if upward else vert
                for col in (right, right - 1):
                    if not self.func[row][col] and idx < len(bits):
                        self.mod[row][col] = bits[idx]
                        idx += 1
            right -= 2

    def masked(self, mask: int) -> list[list[bool]]:
        return [
            [self.mod[r][c] ^ (not self.func[r][c] and mask_bit(mask, r, c)) for c in range(self.size)]
            for r in range(self.size)
        ]


def encode(text: str) -> list[list[bool]]:
    """Encode `text` (UTF-8) in the smallest version 1-10 at level M; ValueError when it does not fit."""
    payload = text.encode("utf-8")
    for version in range(1, MAX_VERSION + 1):
        # 4 mode bits + count bits + 8 bits per byte must fit the data capacity
        if 4 + char_count_bits(version) + 8 * len(payload) <= data_capacity(version) * 8:
            break
    else:
        raise ValueError(f"text of {len(payload)} bytes does not fit a QR code of version {MAX_VERSION}")
    grid = _Grid(version)
    grid.draw_function_patterns(version)
    grid.place_data(_interleave(_data_codewords(payload, version), version))
    best: list[list[bool]] = []
    best_score = -1
    for mask in range(8):
        grid.draw_format(mask)
        candidate = grid.masked(mask)
        score = penalty(candidate)
        if best_score < 0 or score < best_score:
            best, best_score = candidate, score
    return best
