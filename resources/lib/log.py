# resources/lib/log.py
"""Logging that cannot leak secrets: every message passes through mask() before it reaches kodi.log."""
import re

try:
    import xbmc
except ImportError:  # unit tests without Kodi stubs
    xbmc = None

_SECRET_QUERY = re.compile(r"(token|api_key|apikey|key|secret)=[^&\s'\"]+", re.IGNORECASE)
_BEARER = re.compile(r"(bearer\s+)\S+", re.IGNORECASE)
_PATH_SECRET = re.compile(r"(/[A-Za-z0-9_-]{16,})(?=/|$|\s)")


def mask(text):
    """Hide tokens in query strings, Bearer headers and long random path segments (the QR secret)."""
    text = _SECRET_QUERY.sub(r"\1=***", str(text))
    text = _BEARER.sub(r"\1***", text)
    return _PATH_SECRET.sub("/***", text)


def log(message, level=None):
    line = "[abckasefi] " + mask(message)
    if xbmc is not None:
        xbmc.log(line, xbmc.LOGINFO if level is None else level)
    return line
