# resources/lib/watched.py
"""Kodi's own watched state, read from the MyVideos database (read-only).

Kodi records playcount/resume for a plugin item under the path of the item that was listed and resolved. Because our
movie/episode items carry the Nokturno URL (see urls.py), the rows land in `files` with strFilename = that URL and
Kodi decorates our list by itself. Only FOLDERS (series, seasons) are never totalled by Kodi, so this module reads
those rows and aggregates them. Everything here degrades to "no marks" when the database cannot be read.
"""
import re
import sqlite3

from .const import NOKTURNO_BASE
from .log import log

try:
    import xbmcvfs
except ImportError:  # unit tests without Kodi stubs
    xbmcvfs = None

DB_DIR = "special://database/"
DB_NAME_RE = re.compile(r"^MyVideos(\d+)\.db$")
EP_ID_RE = re.compile(r"[?&]id=(tt\d+)%3A(\d+)%3A(\d+)(?:&|$)")
PATH_FILTER = NOKTURNO_BASE  # strPath of every Nokturno row


def db_path():
    """Newest MyVideos<N>.db in Kodi's database folder, or None."""
    if xbmcvfs is None:
        return None
    root = xbmcvfs.translatePath(DB_DIR)
    try:
        _dirs, files = xbmcvfs.listdir(DB_DIR)
    except (OSError, TypeError):
        return None
    versions = sorted((int(m.group(1)), name) for name in files for m in [DB_NAME_RE.match(name)] if m)
    return f"{root.rstrip('/')}/{versions[-1][1]}" if versions else None


def _query(path):
    """Rows (strFilename, playCount) for all Nokturno files, opened read-only. Never raises."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error as exc:
        log(f"watched: cannot open the video database ({type(exc).__name__})")
        return []
    try:
        cur = conn.execute(
            "SELECT files.strFilename, COALESCE(files.playCount, 0) FROM files "
            "JOIN path ON path.idPath = files.idPath WHERE path.strPath = ?", (PATH_FILTER,))
        return cur.fetchall()
    except sqlite3.Error as exc:
        log(f"watched: query failed ({type(exc).__name__})")
        return []
    finally:
        conn.close()


def episode_counts(rows):
    """{tt: {season: {episode: playcount}}} from raw rows; non-episode URLs are ignored."""
    out = {}
    for filename, playcount in rows:
        match = EP_ID_RE.search(filename or "")
        if match:
            tt, season, episode = match.group(1), int(match.group(2)), int(match.group(3))
            out.setdefault(tt, {}).setdefault(season, {})[episode] = int(playcount)
    return out


def load(path=None):
    """Watched episodes per series; {} when the database is missing or unreadable."""
    path = path or db_path()
    return episode_counts(_query(path)) if path else {}


def season_progress(state, tt, season, total):
    """(watched, total) for one season; `total` comes from the catalog (TMDB) because Kodi does not know it."""
    eps = state.get(tt, {}).get(int(season), {})
    return sum(1 for count in eps.values() if count > 0), int(total or 0)


def series_progress(state, tt, season_totals):
    """(watched, total) for a whole series; season_totals = {season: episode_count}. Specials (0) are not counted."""
    done = total = 0
    for season, count in season_totals.items():
        if int(season) == 0:
            continue
        done += season_progress(state, tt, season, count)[0]
        total += int(count or 0)
    return done, total
