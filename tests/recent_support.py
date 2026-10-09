# tests/recent_support.py
"""A temporary MyVideos-like sqlite file and URL builders shared by the recently-watched and resume tests."""

import sqlite3

from resources.lib.const import NOKTURNO_BASE

MOVIE = NOKTURNO_BASE + "?action=play&type=movie&id=tt0000001&ask=1"
OTHER = NOKTURNO_BASE + "?action=play&type=movie&id=tt0000002&ask=1"
EP = NOKTURNO_BASE + "?action=play&type=series&id=tt0000009%3A{}%3A{}&series=tt0000009&ask=1"
EP_OTHER = NOKTURNO_BASE + "?action=play&type=series&id=tt0000008%3A{}%3A{}&series=tt0000008&ask=1"


def make_db(tmp_path, rows, bookmarks=()):
    """rows: (strFilename, lastPlayed, strPath[, playCount]); bookmarks: strFilename that have a resume point, or
    {strFilename: (timeInSeconds, totalTimeInSeconds)}."""
    path = str(tmp_path / "MyVideos999.db")
    conn = sqlite3.connect(path)
    conn.executescript(
        "CREATE TABLE path(idPath INTEGER PRIMARY KEY, strPath TEXT);"
        "CREATE TABLE files(idFile INTEGER PRIMARY KEY, idPath INTEGER, strFilename TEXT, playCount INTEGER, "
        "lastPlayed TEXT);"
        "CREATE TABLE bookmark(idBookmark INTEGER PRIMARY KEY, idFile INTEGER, timeInSeconds DOUBLE, "
        "totalTimeInSeconds DOUBLE, type INTEGER);"
    )
    points = bookmarks if isinstance(bookmarks, dict) else dict.fromkeys(bookmarks, (60.0, 3600.0))
    paths = {}
    for number, (name, played, folder, *count) in enumerate(rows, 1):
        if folder not in paths:
            paths[folder] = len(paths) + 1
            conn.execute("INSERT INTO path VALUES (?, ?)", (paths[folder], folder))
        conn.execute("INSERT INTO files VALUES (?, ?, ?, ?, ?)", (number, paths[folder], name, *(count or [1]), played))
        if name in points:
            conn.execute("INSERT INTO bookmark VALUES (?, ?, ?, ?, 1)", (number, number, *points[name]))
    conn.commit()
    conn.close()
    return path
