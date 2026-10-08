# resources/lib/urls.py
"""The ONLY place that builds plugin URLs.

Kodi shows a watched mark on a plugin list item only when the item path is a BYTE-IDENTICAL string to the one it
stored at playback. The Nokturno URLs below therefore never change shape, parameter order or encoding; they are the
same strings Nokturno's own TMDb Helper player uses, so the watched state is even shared with it.
"""
import re
from urllib.parse import parse_qsl, urlencode

from .const import NOKTURNO_BASE, SELF_BASE

TT_RE = re.compile(r"^tt\d{1,10}$")


def check_tt(tt):
    """Return `tt` when it is a valid IMDb id, else raise ValueError (ids end up in URLs and API paths)."""
    if not isinstance(tt, str) or not TT_RE.match(tt):
        raise ValueError(f"not an IMDb id: {tt!r}")
    return tt


def build_url(**params):
    """URL of this plugin; None values are skipped, parameter order is the call order."""
    query = urlencode([(k, v) for k, v in params.items() if v is not None])
    return SELF_BASE + (f"?{query}" if query else "")


def parse_query(query):
    """'?a=1&b=2' (or 'a=1&b=2') -> {'a': '1', 'b': '2'}; later duplicates win."""
    return dict(parse_qsl(query.lstrip("?"), keep_blank_values=True))


def nokturno_movie_url(tt):
    return f"{NOKTURNO_BASE}?action=play&type=movie&id={check_tt(tt)}&ask=1"


def nokturno_episode_url(tt, season, episode):
    # the colons of `tt:S:E` are percent-encoded (%3A) exactly as Nokturno's own player URL writes them
    return f"{NOKTURNO_BASE}?action=play&type=series&id={check_tt(tt)}%3A{int(season)}%3A{int(episode)}&series={tt}&ask=1"


def nokturno_series_url(tt):
    return f"{NOKTURNO_BASE}?action=seasons&id={check_tt(tt)}"
