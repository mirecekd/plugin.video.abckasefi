# resources/lib/listing_common.py
"""Helpers shared by the listing screens: parameter checks, chunked directory output, item routing by type."""
import re

import xbmcgui
import xbmcplugin

from . import items, texts, totals, watched
from .const import KINDS, S_ADDON_NAME
from .log import log

CHUNK = 200  # items per xbmcplugin.addDirectoryItems call
LETTER_RE = re.compile(r"^(?:[A-Z]|0-9)$")
KEY_RE = re.compile(r"^[A-Za-z0-9_-]{1,64}$")


def check_kind(value):
    if value not in KINDS:
        raise ValueError(f"bad kind: {value!r}")
    return value


def check_letter(value):
    if not LETTER_RE.match(value or ""):
        raise ValueError(f"bad letter: {value!r}")
    return value


def check_key(value):
    if not KEY_RE.match(value or ""):
        raise ValueError(f"bad list key: {value!r}")
    return value


def pick(value, allowed, default):
    """`value` when it is one of `allowed`, else `default` (unknown sort names fall back quietly)."""
    return value if value in allowed else default


def page_number(value):
    try:
        return max(1, int(value))
    except (TypeError, ValueError):
        return 1


def notify(message, icon=xbmcgui.NOTIFICATION_INFO):
    xbmcgui.Dialog().notification(texts.t(S_ADDON_NAME), message, icon)


def entries_for(data, catalog, kind=None):
    """(path, ListItem, isFolder) for every API item; `kind` forces movie/series, else each item's own `type`.

    Items that cannot be built (missing or malformed id) are skipped and logged instead of failing the whole page.
    Series folders get a watched mark when their episode count is known (learned when the user opened them, see
    totals.py) and Kodi's database says every episode was played.
    """
    out = []
    state, known = None, None
    for entry in data.get("items") or []:
        try:
            if (kind or entry.get("type")) == "series":
                if state is None:  # read the two small sources once per page, and only if a series is on it
                    state, known = watched.load(), totals.load()
                out.append(items.series_item(entry, catalog, series_progress(state, known, entry.get("id"))))
            else:
                out.append(items.movie_item(entry, catalog))
        except (KeyError, ValueError, TypeError) as exc:
            log(f"skipped a malformed catalog item ({type(exc).__name__})")
    return out


def series_progress(state, known, tt):
    """(watched, total) for a series whose season sizes are known, else None (no mark rather than a wrong one)."""
    seasons = (known or {}).get(tt)
    if not seasons:
        return None
    return watched.series_progress(state or {}, tt, seasons)


def content_for(data, kind=None):
    """Kodi content type: by `kind` when given, else by what the items are (mixed search results -> videos)."""
    if kind:
        return "tvshows" if kind == "series" else "movies"
    types = {entry.get("type") for entry in data.get("items") or []}
    if types == {"series"}:
        return "tvshows"
    return "movies" if types == {"movie"} else "videos"


def close_failed(handle):
    """End a directory without items and without navigating (the user stays on the previous screen)."""
    xbmcplugin.endOfDirectory(handle, succeeded=False)


def show(handle, entries, content, update=False):
    """Hand the entries to Kodi in chunks of CHUNK and close the directory (never cached: watched marks change)."""
    for start in range(0, len(entries), CHUNK):
        xbmcplugin.addDirectoryItems(handle, entries[start:start + CHUNK], len(entries))
    xbmcplugin.setContent(handle, content)
    xbmcplugin.addSortMethod(handle, xbmcplugin.SORT_METHOD_NONE)
    xbmcplugin.endOfDirectory(handle, succeeded=True, updateListing=update, cacheToDisc=False)
