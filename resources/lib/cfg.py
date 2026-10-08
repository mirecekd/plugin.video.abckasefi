# resources/lib/cfg.py
"""Typed access to the add-on settings and validation of what the user (or the phone form) enters."""
import re
from urllib.parse import urlsplit

from .const import LANGS, PER_PAGE_DEFAULT, PER_PAGE_MAX, PER_PAGE_MIN, PER_PAGE_STEP

try:
    import xbmcaddon
except ImportError:  # unit tests without Kodi stubs
    xbmcaddon = None

TOKEN_RE = re.compile(r"^[\x21-\x7e]{1,256}$")  # printable ASCII, no whitespace
MAX_URL = 500


def _addon():
    return xbmcaddon.Addon() if xbmcaddon is not None else None


def get(key, default=""):
    addon = _addon()
    return addon.getSetting(key) if addon is not None else default


def put(key, value):
    addon = _addon()
    if addon is not None:
        addon.setSetting(key, str(value))


def clamp_per_page(value):
    """Items per page: integer, clamped to 20..200 and rounded to a multiple of 10."""
    try:
        number = int(float(value))
    except (TypeError, ValueError):
        return PER_PAGE_DEFAULT
    number = max(PER_PAGE_MIN, min(PER_PAGE_MAX, number))
    # round half UP (Python's round() is banker's rounding: 45 would become 40 but 55 would become 60)
    return int((number + PER_PAGE_STEP // 2) // PER_PAGE_STEP * PER_PAGE_STEP)


def normalize_url(url):
    """Trim blanks and trailing slashes: 'http://host:8090/ ' -> 'http://host:8090'."""
    return (url or "").strip().rstrip("/")


def validate_url(url):
    """(ok, reason). http and https are both allowed (http for a home LAN); https is always verified at connect time."""
    url = normalize_url(url)
    if not url or len(url) > MAX_URL:
        return False, "empty or too long"
    try:
        parts = urlsplit(url)
        hostname, _port = parts.hostname, parts.port
    except ValueError:
        return False, "malformed"
    if parts.scheme not in ("http", "https") or not hostname:
        return False, "must start with http:// or https:// and name a host"
    if parts.username or parts.password:
        return False, "credentials in the URL are not allowed"
    if parts.query or parts.fragment:
        return False, "no query or fragment"
    return True, ""


def validate_token(token):
    """Token may be empty (catalog without API_TOKEN); otherwise printable ASCII, no spaces, <= 256."""
    token = (token or "").strip()
    return (token == "" or bool(TOKEN_RE.match(token))), token


def base_url():
    return normalize_url(get("catalog_url"))


def token():
    return get("api_token").strip()


def per_page():
    return clamp_per_page(get("items_per_page", str(PER_PAGE_DEFAULT)) or PER_PAGE_DEFAULT)


def lang():
    try:
        return LANGS[int(get("lang", "0") or 0)]
    except (ValueError, IndexError):
        return LANGS[0]


def configured():
    return validate_url(base_url())[0]
