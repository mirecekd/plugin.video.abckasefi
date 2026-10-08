# tools/qr_check.py
"""Manual check: render strings with resources/lib/qr.py + png.py and decode them with an independent decoder.

Usage: /tmp/qrref/bin/python tools/qr_check.py [--compare]
Needs zxing-cpp + Pillow, or opencv-python-headless + numpy, or pyzbar + Pillow. With --compare each matrix is also
compared module by module with python-qrcode (level M, same version, mask pinned to the mask this encoder chose, so
data encoding, Reed-Solomon, interleaving, function patterns, format and version bits are proven identical) and the
penalty score is compared with python-qrcode's lost_point() of the same matrix. Prints PASS/FAIL per string and
exits non-zero on any failure.
"""
import importlib
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

from resources.lib import png, qr  # noqa: E402
from resources.lib.qr_ecc import format_bits  # noqa: E402
from resources.lib.qr_penalty import penalty  # noqa: E402

URL = "http://192.168.1.20:43211/Xk3_9aB-c2D4eF6gH8iJkQ"
# byte-mode capacity per version at level M
CAPS = {1: 14, 2: 26, 3: 42, 4: 62, 5: 84, 6: 106, 7: 122, 8: 152, 9: 180, 10: 213}


def sample_strings():
    out = [
        "A",
        "ab",
        "Hello, world!",
        URL,
        "https://example.com/" + "x" * 30,
        "Příliš žluťoučký kůň úpěl ďábelské ódy",
        "日本語のテキスト QR",
        "ŘŠČ ěščřžýáíé",
        "0123456789" * 3,
        URL + "?token=" + "t" * 40,
    ]
    for version, cap in CAPS.items():
        out.append((f"v{version}-" + "abcdefghij" * 30)[:cap])
        if version < max(CAPS):
            out.append((f"v{version}+" + "klmnopqrst" * 30)[: cap + 1])
    return out


def _load(name):
    try:
        return importlib.import_module(name)
    except ImportError:
        return None


def find_decoder():
    """Return (name, function PNG bytes -> decoded text or None) of the first available decoder."""
    pil = _load("PIL.Image")
    zxing = _load("zxingcpp")
    if zxing and pil:

        def decode_zxing(data):
            res = zxing.read_barcodes(pil.open(io.BytesIO(data)))
            return res[0].text if res else None

        return "zxing-cpp", decode_zxing
    cv2 = _load("cv2")
    numpy = _load("numpy")
    if cv2 and numpy:

        def decode_cv(data):
            img = cv2.imdecode(numpy.frombuffer(data, numpy.uint8), cv2.IMREAD_GRAYSCALE)
            text, _, _ = cv2.QRCodeDetector().detectAndDecode(img)
            return text or None

        return "opencv QRCodeDetector", decode_cv
    zbar = _load("pyzbar.pyzbar")
    if zbar and pil:

        def decode_zbar(data):
            res = zbar.decode(pil.open(io.BytesIO(data)))
            return res[0].data.decode("utf-8") if res else None

        return "pyzbar", decode_zbar
    return None, None


def reference_matrix(text, version, mask):
    """python-qrcode's matrix (and its lost_point of it) for the same payload, version and mask."""
    qrcode = importlib.import_module("qrcode")
    util = importlib.import_module("qrcode.util")
    code = qrcode.QRCode(version=version, error_correction=qrcode.ERROR_CORRECT_M, border=0, mask_pattern=mask)
    code.add_data(util.QRData(text.encode("utf-8"), mode=util.MODE_8BIT_BYTE))
    code.make(fit=False)
    matrix = [[bool(v) for v in row] for row in code.get_matrix()]
    return matrix, util.lost_point(code.modules)


def mask_of(matrix):
    """Mask pattern recorded in the format information (bits 0-7 are on row 8, right to left)."""
    n = len(matrix)
    low = sum(int(matrix[8][n - 1 - i]) << i for i in range(8))
    for mask in range(8):
        if format_bits(mask) & 0xFF == low:
            return mask
    raise ValueError("unreadable format information")


def main(argv):
    name, decode = find_decoder()
    if decode is None:
        print("FAIL: no independent QR decoder available; correctness NOT verified")
        return 2
    print(f"decoder: {name}")
    failures = 0
    samples = sample_strings()
    for text in samples:
        try:
            matrix = qr.encode(text)
            version = (len(matrix) - 17) // 4
            ok = decode(png.to_png(matrix, scale=6, border=4)) == text
            detail = f"v{version} decode"
            if "--compare" in argv:
                ref, ref_penalty = reference_matrix(text, version, mask_of(matrix))
                same = matrix == ref and penalty(matrix) == ref_penalty
                ok = ok and same
                detail += f", identical to python-qrcode={same}"
        except Exception as exc:  # report every string, do not abort
            ok, detail = False, repr(exc)
        failures += 0 if ok else 1
        print(f"{'PASS' if ok else 'FAIL'} {len(text)} chars {detail} {text[:40]!r}")
    print(f"{len(samples) - failures}/{len(samples)} passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
