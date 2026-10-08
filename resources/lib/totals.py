# resources/lib/totals.py
"""Remembers how many episodes each series has, learned for free whenever the user opens a series.

Kodi does not total watched episodes for plugin folders, and a title list does not carry season sizes. Asking the catalog
for the seasons of every series in a 100-row page would be 100 requests, so instead the seasons screen records the
counts here and the lists use them. A series nobody opened yet simply has no mark. Everything degrades to "no data".
"""
import json
import os

from .log import log

try:
    import xbmcvfs
except ImportError:  # unit tests without Kodi stubs
    xbmcvfs = None

FILE_NAME = "series_totals.json"
PROFILE_DIR = "special://profile/addon_data/plugin.video.abckasefi/"
MAX_SERIES = 5000  # keeps the file around a few hundred kB


def _path():
    if xbmcvfs is None:
        return None
    try:
        folder = xbmcvfs.translatePath(PROFILE_DIR)
    except (OSError, TypeError, AttributeError):
        return None
    return os.path.join(folder, FILE_NAME) if folder else None


def load(path=None):
    """{tt: {season: episode_count}}; {} when the file is missing, unreadable or malformed."""
    path = path or _path()
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except (OSError, ValueError) as exc:
        log(f"totals: cannot read the cache ({type(exc).__name__})")
        return {}
    out = {}
    if isinstance(raw, dict):
        for tt, seasons in raw.items():
            if isinstance(seasons, dict):
                out[tt] = {int(s): int(c) for s, c in seasons.items() if str(s).lstrip("-").isdigit() and str(c).isdigit()}
    return out


def save(tt, season_counts, path=None):
    """Store {season: count} for one series (replacing what was there). Never raises."""
    path = path or _path()
    if not path:
        return
    data = load(path)
    data[tt] = {int(s): int(c) for s, c in season_counts.items()}
    while len(data) > MAX_SERIES:
        data.pop(next(iter(data)))  # oldest first (dicts keep insertion order)
    tmp = f"{path}.tmp"
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(tmp, "w", encoding="utf-8") as handle:
            json.dump(data, handle)
        os.replace(tmp, path)  # readers never see a half-written file
    except OSError as exc:
        log(f"totals: cannot write the cache ({type(exc).__name__})")
