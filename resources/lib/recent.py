# resources/lib/recent.py
"""Recently watched titles, read from Kodi's own MyVideos database (read-only, like watched.py).

A title counts as recent when Kodi stored a last-played time or a resume point for its Nokturno URL. Movies are listed
as such; for series only the newest episode is kept, so the list answers "where was I" instead of repeating a show.
Every row also carries the playback state of that file (play count, resume point).
Everything degrades to an empty list when the database cannot be read.
"""

import re
import sqlite3
from typing import NamedTuple

from . import watched
from .const import NOKTURNO_BASE
from .log import log

MAX_ITEMS = 30
MAX_ROWS = 2000  # rows read before the per-title dedup; a series has many episode rows
KIND_NEEDLES = {"movie": "&type=movie&", "series": "&type=series&"}  # as written by urls.py
MOVIE_RE = re.compile(r"[?&]id=(tt\d+)(?:&|$)")
PLAY_RE = re.compile(r"[?&]action=play(?:&|$)")


class State(NamedTuple):
    """Playback state of one file; the resume and total seconds are 0 when Kodi stored no resume point."""

    last_played: str
    play_count: int
    resume_seconds: float
    total_seconds: float


def _rows(path, tt=None, kind=None):
    """[(strFilename, State)], newest last-played first (files with only a resume point come after, newest row first).

    `tt` limits the rows to one series, `kind` ('movie' | 'series') to that type; both filter before the row limit.
    """
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True, timeout=2)
    except sqlite3.Error as exc:
        log(f"recent: cannot open the video database ({type(exc).__name__})")
        return []
    needle = "" if tt is None else f"id={tt}%3A"  # empty = no series filter
    kind_needle = KIND_NEEDLES.get(kind or "", "")  # empty = no type filter
    try:
        # a title is recent when Kodi stored a last-played time or a resume bookmark (type 1) for its Nokturno URL
        cur = conn.execute(
            "SELECT f.strFilename, COALESCE(f.lastPlayed, ''), COALESCE(f.playCount, 0), "
            "COALESCE(b.timeInSeconds, 0), COALESCE(b.totalTimeInSeconds, 0) "
            "FROM files f JOIN path p ON p.idPath = f.idPath "
            "LEFT JOIN bookmark b ON b.idFile = f.idFile AND b.type = 1 "
            "WHERE p.strPath = ? AND (COALESCE(f.lastPlayed, '') <> '' OR b.idBookmark IS NOT NULL) "
            "AND (? = '' OR instr(f.strFilename, ?) > 0) "
            "AND (? = '' OR instr(f.strFilename, ?) > 0) "
            "ORDER BY COALESCE(f.lastPlayed, '') DESC, f.idFile DESC LIMIT ?",
            (NOKTURNO_BASE, needle, needle, kind_needle, kind_needle, MAX_ROWS),
        )
        return [
            (name, State(played, int(count), float(resume), float(total)))
            for name, played, count, resume, total in cur.fetchall()
        ]
    except (sqlite3.Error, TypeError, ValueError) as exc:
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


def recent_with_state(path=None, limit=MAX_ITEMS, kind=None):
    """Newest first: [(entry, State)], entry = ('movie', tt) | ('episode', tt, season, episode); one per movie and series.

    The episode kept for a series is the one played last (newest last-played stamp), not the highest episode number.
    `kind` ('movie' | 'series'; anything else = both) is applied before `limit`, so the limit counts only that type.
    """
    path = path or watched.db_path()
    wanted = {"movie": "movie", "series": "episode"}.get(kind or "")
    out, seen = [], set()
    for filename, state in _rows(path, kind=kind) if path else []:
        entry = parse(filename)
        if entry is None or entry[1] in seen or (wanted and entry[0] != wanted):
            continue
        seen.add(entry[1])
        out.append((entry, state))
        if len(out) >= limit:
            break
    return out


def recent(path=None, limit=MAX_ITEMS, kind=None):
    """Newest first: [('movie', tt) | ('episode', tt, season, episode)], one entry per movie and per series."""
    return [entry for entry, _state in recent_with_state(path, limit, kind)]


def last_episode(tt, path=None):
    """(season, episode, State) of the episode of series `tt` that was played last, or None when none is stored."""
    path = path or watched.db_path()
    for filename, state in _rows(path, tt) if path else []:
        entry = parse(filename)
        if entry is not None and entry[0] == "episode" and entry[1] == tt:
            return entry[2], entry[3], state
    return None
