# tests/test_qr.py
"""QR encoder (resources/lib/qr*.py) and PNG writer (png.py): structural invariants plus golden matrices.

The golden matrices were decoded back to the input text with zxing-cpp and are identical to python-qrcode's output for
the same version and mask (see tools/qr_check.py --compare), so they pin the exact bit layout. PNG output is tested in test_qr_png.py.
"""
import pytest

from resources.lib import qr
from resources.lib.qr_ecc import generator_poly, rs_remainder

URL = "http://192.168.1.20:43211/Xk3_9aB-c2D4eF6gH8iJkQ"
LONG = ("v6+" + "klmnopqrst" * 30)[:107]

GOLDEN = {
    "A": (
        "fe93f8 82fa08 ba2ae8 badae8 ba72e8 825a08 feabf8 00d800 b73a58 595e40 ced068 b413e0 9e4920 00b248 "
        "fe9940 82c1b0 ba6f88 baf3f0 baab00 822528 fe8480"
    ),
    URL: (
        "fe07d3bf8 8257c4a08 ba946f2e8 baf38eae8 baed212e8 82ffeca08 feaaaabf8 00e304800 be6de93e0 75fa11f68 "
        "c3a1a04a0 087a14ce8 4e40325c0 391b89858 2e9472970 ed54bcc60 1a5079188 04ecd3f60 debb40cb0 5127672f0 "
        "e6068f8c0 918326728 a381ac350 8d0d07420 b6b5e8fc0 00f7948a8 fe4da5ab0 8296968b0 ba8024fc8 bae3881b8 "
        "bac432f00 827a9c5e0 feca79bb0"
    ),
    LONG: (
        "fe24d25f8bf8 822f25f0d208 bac7616cd2e8 ba8bfe231ae8 babddfe73ae8 82c2a8918208 feaaaaaaabf8 00fe788cc800 "
        "be293fc753e0 9958fad61d38 52e32171bac0 70583804cfe8 7f2bef311450 41445c439de8 13d4b9f2aab0 2d5ff48ccfe0 "
        "efc961637210 41b1c2461c18 b683bdf132d0 6883110cd7f8 8fa57fc73f80 18a9589618f8 cacd5ad1ba90 e8a1188cc8a8 "
        "dfedcfa11f80 00be3e4f8e78 e3d96268a530 c8935994d6f8 9e93b8e96f88 216987dc0c18 d7db0beb24d0 91d226cdd3f8 "
        "3a1e29872780 7cb8ded79258 0a09ea303c30 78e53fec92e8 9a629fa14f80 00c608ef8898 fe26fa88fad0 82eeb89cd8f0 "
        "ba96efe57f80 ba948b5e1788 bad75c6d3e50 8276ca43cd60 febed1972e90"
    ),
}

# format information bit positions, bit 14 first
FORMAT_COPY_1 = [(8, 0), (8, 1), (8, 2), (8, 3), (8, 4), (8, 5), (8, 7), (8, 8), (7, 8), (5, 8), (4, 8), (3, 8),
                 (2, 8), (1, 8), (0, 8)]


def format_copy_2(n):
    """Bits 14..8 down the left of the bottom-left finder, bits 7..0 along the top-right finder."""
    return [(n - 1 - i, 8) for i in range(7)] + [(8, n - 8 + i) for i in range(8)]


def read_bits(m, positions):
    value = 0
    for r, c in positions:
        value = (value << 1) | int(m[r][c])
    return value


def parse_golden(packed, size):
    pad = len(packed.split()[0]) * 4 - size
    return [[(int(row, 16) >> (pad + size - 1 - c)) & 1 == 1 for c in range(size)] for row in packed.split()]


def version_of(matrix):
    return (len(matrix) - 17) // 4


def bch_remainder(value, generator):
    while value.bit_length() >= generator.bit_length():
        value ^= generator << (value.bit_length() - generator.bit_length())
    return value


@pytest.mark.parametrize("text", list(GOLDEN))
def test_golden_matrices_are_reproduced_exactly(text):
    matrix = qr.encode(text)
    assert [list(row) for row in matrix] == parse_golden(GOLDEN[text], len(matrix))


@pytest.mark.parametrize(
    "length, version",
    [(1, 1), (14, 1), (15, 2), (26, 2), (27, 3), (42, 3), (43, 4), (62, 4), (63, 5), (84, 5), (85, 6), (106, 6),
     (107, 7), (122, 7), (123, 8), (152, 8), (153, 9), (180, 9), (181, 10), (213, 10)],
)
def test_smallest_fitting_version_is_chosen_at_every_capacity_boundary(length, version):
    matrix = qr.encode("x" * length)
    assert version_of(matrix) == version
    assert len(matrix) == 17 + 4 * version
    assert all(len(row) == len(matrix) for row in matrix)


def test_text_that_does_not_fit_version_10_raises_value_error():
    with pytest.raises(ValueError):
        qr.encode("x" * 214)


def test_capacity_is_measured_in_utf8_bytes_not_characters():
    assert version_of(qr.encode("\u00e1" * 7)) == 1  # 14 bytes
    assert version_of(qr.encode("\u00e1" * 8)) == 2  # 16 bytes
    with pytest.raises(ValueError):
        qr.encode("\u00e1" * 107)  # 214 bytes


def test_matrix_holds_plain_bools():
    assert all(isinstance(m, bool) for row in qr.encode("abc") for m in row)


@pytest.mark.parametrize("text", ["a", URL, "x" * 100, "x" * 213, "\u010d\u0159\u017e"])
def test_finders_separators_timing_and_dark_module(text):
    m = qr.encode(text)
    n = len(m)
    for top, left in ((0, 0), (0, n - 7), (n - 7, 0)):
        for r in range(7):
            for c in range(7):
                assert m[top + r][left + c] == (max(abs(r - 3), abs(c - 3)) != 2)
    for i in range(8):  # separators
        assert not m[7][i] and not m[i][7]
        assert not m[7][n - 1 - i] and not m[i][n - 8]
        assert not m[n - 8][i] and not m[n - 1 - i][7]
    for i in range(8, n - 8):
        assert m[6][i] == (i % 2 == 0)
        assert m[i][6] == (i % 2 == 0)
    assert m[n - 8][8] is True


def test_alignment_patterns_are_drawn_where_required():
    m = qr.encode("x" * 20)  # version 2: one pattern centred on (18, 18)
    assert version_of(m) == 2
    for r in range(-2, 3):
        for c in range(-2, 3):
            assert m[18 + r][18 + c] == (max(abs(r), abs(c)) != 1)
    m = qr.encode("x" * 150)  # version 8: centres 6/24/42; the three finder corners get none
    assert version_of(m) == 8
    for r, c in ((24, 24), (42, 42), (24, 42), (42, 24)):
        assert m[r][c] and not m[r][c + 1] and m[r][c + 2] and not m[r + 1][c] and m[r + 2][c]


@pytest.mark.parametrize("text", ["a", URL, "x" * 100, "x" * 213, "\u010d" * 5])
def test_format_information_is_a_valid_bch_codeword_for_level_m_in_both_copies(text):
    m = qr.encode(text)
    for positions in (FORMAT_COPY_1, format_copy_2(len(m))):
        value = read_bits(m, positions) ^ 0x5412
        assert value >> 13 == 0  # error correction level M is indicator 00
        assert bch_remainder(value, 0x537) == 0


def test_both_format_copies_carry_the_same_bits():
    m = qr.encode(URL)
    assert read_bits(m, FORMAT_COPY_1) == read_bits(m, format_copy_2(len(m)))


@pytest.mark.parametrize("version, text", [(7, "x" * 110), (8, "x" * 150), (10, "x" * 213)])
def test_version_information_for_large_versions_is_a_valid_bch_codeword(version, text):
    m = qr.encode(text)
    n = len(m)
    assert version_of(m) == version
    bottom_left = sum(int(m[n - 11 + i % 3][i // 3]) << i for i in range(18))
    top_right = sum(int(m[i // 3][n - 11 + i % 3]) << i for i in range(18))
    assert bottom_left == top_right
    assert bottom_left >> 12 == version
    assert bch_remainder(bottom_left, 0x1F25) == 0


def test_reed_solomon_matches_the_published_hello_world_example():
    data = [32, 91, 11, 120, 209, 114, 220, 77, 67, 64, 236, 17, 236, 17, 236, 17]
    assert rs_remainder(data, 10) == [196, 35, 39, 119, 235, 215, 231, 226, 93, 23]
    assert generator_poly(7) == [127, 122, 154, 164, 11, 68, 117]


def test_encoding_is_deterministic_and_depends_on_the_text():
    assert qr.encode(URL) == qr.encode(URL)
    assert qr.encode(URL) != qr.encode(URL[:-1] + "R")

