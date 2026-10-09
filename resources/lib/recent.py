# resources/lib/recent.py
"""Recently watched titles, read from Kodi's own MyVideos database (read-only, like watched.py).

A title counts as recent when Kodi stored a last-played time or a resume point for its Nokturno URL. Movies are listed
as such; for series only the newest episode is kept, so the list answers "where was I" instead of repeating a show.
Everything degrades to an empty list when the database cannot be read.
"""
import re
import sqlite3

from . import watched
from .const import NOKTURNO_BASE
from .log import log

MAX_ITEMS = 30
MOVIE_RE = re.compile(r"[?&]id=(tt\d+)(?:&|$)")
PLAY_RE = re.compile(r"[?&]action=play(?:&|$)")


def _rows(path):
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error as exc:
        log(f"recent: cannot open the video database ({type(exc).__name__})")
        return []
    try:
        # a title is recent when Kodi stored a last-played time or a resume bookmark (type 1) for its Nokturno URL
        cur = conn.execute(
            "SELECT f.strFilename, COALESCE(f.lastPlayed, '') FROM files f JOIN path p ON p.idPath = f.idPath "
            "LEFT JOIN bookmark b ON b.idFile = f.idFile AND b.type = 1 "
            "WHERE p.strPath = ? AND (COALESCE(f.lastPlayed, '') <> '' OR b.idBookmark IS NOT NULL) "
            "ORDER BY COALESCE(f.lastPlayed, '') DESC LIMIT 400", (NOKTURNO_BASE,))
        return cur.fetchall()
    except sqlite3.Error as exc:
        log(f"recent: query failed ({type(exc).__name__})")
        return []
    finally:
        conn.close()


def parse(filename):
    """('movie', tt) or ('episode', tt, season, episode) for a Nokturno play URL, else None."""
    if not PLAY_RE.search(filename or ""):
        return None
    episode = watched.EP_ID_RE.search(filename)
    if episode:
        return "episode", episode.group(1), int(episode.group(2)), int(episode.group(3))
    movie = MOVIE_RE.search(filename)
    return ("movie", movie.group(1)) if movie and "type=movie" in filename else None


def recent(path=None, limit=MAX_ITEMS):
    """Newest first: [('movie', tt) | ('episode', tt, season, episode)], one entry per movie and per series."""
    path = path or watched.db_path()
    out, seen = [], set()
    for filename, _played in _rows(path) if path else []:
        entry = parse(filename)
        if entry is None or entry[1] in seen:
            continue
        seen.add(entry[1])
        out.append(entry)
        if len(out) >= limit:
            break
    return out
