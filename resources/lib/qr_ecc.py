# resources/lib/qr_ecc.py
"""Reed-Solomon over GF(256) (poly 0x11D) and the BCH codes of the QR format/version information."""
from __future__ import annotations

from .qr_tables import FORMAT_GENERATOR, FORMAT_MASK, VERSION_GENERATOR

_EXP = [0] * 512
_LOG = [0] * 256


def _init_tables() -> None:
    x = 1
    for i in range(255):
        _EXP[i] = x
        _LOG[x] = i
        x <<= 1
        if x & 0x100:
            x ^= 0x11D
    for i in range(255, 512):
        _EXP[i] = _EXP[i - 255]


_init_tables()


def gf_mul(a: int, b: int) -> int:
    if a == 0 or b == 0:
        return 0
    return _EXP[_LOG[a] + _LOG[b]]


def generator_poly(degree: int) -> list[int]:
    """Coefficients (highest power first, leading 1 omitted) of prod (x - 2^i), i < degree."""
    poly = [1]
    for i in range(degree):
        nxt = poly + [0]
        for j, coef in enumerate(poly):
            nxt[j + 1] ^= gf_mul(coef, _EXP[i])
        poly = nxt
    return poly[1:]


def rs_remainder(data: list[int], degree: int) -> list[int]:
    """The `degree` error-correction codewords of `data`."""
    gen = generator_poly(degree)
    rem = [0] * degree
    for byte in data:
        factor = byte ^ rem[0]
        rem = rem[1:] + [0]
        for i, coef in enumerate(gen):
            rem[i] ^= gf_mul(coef, factor)
    return rem


def format_bits(mask: int) -> int:
    """15-bit format information for level M (indicator 00) and mask pattern `mask`, after the XOR mask."""
    rem = mask
    for _ in range(10):
        rem = (rem << 1) ^ ((rem >> 9) * FORMAT_GENERATOR)
    return ((mask << 10) | rem) ^ FORMAT_MASK


def version_bits(version: int) -> int:
    """18-bit version information (versions 7 and up)."""
    rem = version
    for _ in range(12):
        rem = (rem << 1) ^ ((rem >> 11) * VERSION_GENERATOR)
    return (version << 12) | rem
