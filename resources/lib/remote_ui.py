# resources/lib/remote_ui.py
"""QR dialog for the phone setup: white panel, QR image and the URL as text (fallback when the QR cannot be scanned)."""
import contextlib
import os
import struct
import zlib

import xbmcgui
import xbmcvfs

from . import const, remote_page

CLOSE_ACTIONS = (9, 10, 13, 92)  # parent dir, previous menu, stop, nav back
BLACK = "FF000000"


def qr_png(url):
    """PNG bytes of the QR code for `url`. qr.py and png.py are imported here so nothing else depends on them."""
    from . import png, qr
    return png.to_png(qr.encode(url), const.PNG_SCALE, 4)


def white_png():
    """A 2x2 all-white greyscale PNG used as the background panel."""
    def chunk(kind, data):
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", zlib.crc32(kind + data) & 0xFFFFFFFF)

    raw = (b"\x00" + b"\xff\xff") * 2
    header = struct.pack(">IIBBBBB", 2, 2, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", header) + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


def temp_file(run_id, name, data):
    """Write `data` to special://temp/ under a per-run unique name (Kodi caches textures by path) and return the real
    path. The name carries a random run id, never the URL secret."""
    real = xbmcvfs.translatePath(f"special://temp/abckasefi_{name}_{run_id}.png")
    with open(real, "wb") as handle:
        handle.write(data)
    return real


def remove_files(paths):
    for path in paths:
        with contextlib.suppress(OSError):
            os.remove(path)


def _label(y, text, font):
    return xbmcgui.ControlLabel(320, y, 640, 40, text, font=font, textColor=BLACK, alignment=2)


class QrDialog(xbmcgui.WindowDialog):
    """Non-blocking window: show() returns at once; `closed` turns True when the user backs out."""

    def __init__(self, background_path, qr_path, url):
        super().__init__()
        self.closed = False
        self.addControl(xbmcgui.ControlImage(300, 40, 680, 640, background_path))
        self.addControl(_label(60, remote_page.text(const.S_RM_TITLE), "font14"))
        self.addControl(_label(110, remote_page.text(const.S_RM_SCAN), "font12"))
        self.addControl(xbmcgui.ControlImage(440, 160, 400, 400, qr_path))
        self.addControl(_label(580, remote_page.text(const.S_RM_OPEN), "font12"))
        self.addControl(_label(620, url, "font12"))

    def onAction(self, action):
        if action.getId() in CLOSE_ACTIONS:
            self.closed = True
            self.close()
