# tests/test_recent_state.py
"""recent.py playback state: last-played stamp, play count and resume point read next to each Nokturno file."""

import sqlite3

from resources.lib import recent
from resources.lib.const import NOKTURNO_BASE
from tests.recent_support import EP, EP_OTHER, MOVIE, make_db


def test_state_carries_play_count_and_resume_point(tmp_path):
    path = make_db(
        tmp_path,
        [(EP.format(1, 2), "2026-03-01 10:00:00", NOKTURNO_BASE, 2)],
        bookmarks={EP.format(1, 2): (1380.0, 2700.0)},
    )
    assert recent.recent_with_state(path) == [
        (("episode", "tt0000009", 1, 2), recent.State("2026-03-01 10:00:00", 2, 1380.0, 2700.0))
    ]


def test_state_without_bookmark_has_zero_resume(tmp_path):
    path = make_db(tmp_path, [(MOVIE, "2026-01-01 10:00:00", NOKTURNO_BASE, 1)])
    assert recent.recent_with_state(path) == [
        (("movie", "tt0000001"), recent.State("2026-01-01 10:00:00", 1, 0.0, 0.0))
    ]


def test_only_bookmark_type_one_counts_as_resume_point(tmp_path):
    path = make_db(tmp_path, [(MOVIE, "2026-01-01 10:00:00", NOKTURNO_BASE)])
    conn = sqlite3.connect(path)
    conn.execute("INSERT INTO bookmark VALUES (50, 1, 99.0, 100.0, 2)")  # type 2 = episode bookmark of another kind
    conn.commit()
    conn.close()
    assert recent.recent_with_state(path)[0][1].resume_seconds == 0.0


def test_last_episode_is_the_one_played_last_not_the_highest_number(tmp_path):
    path = make_db(
        tmp_path,
        [
            (EP.format(1, 9), "2026-01-01 10:00:00", NOKTURNO_BASE),
            (EP.format(1, 2), "2026-03-01 10:00:00", NOKTURNO_BASE),  # newest stamp, lowest number
            (EP.format(2, 5), "2026-02-01 10:00:00", NOKTURNO_BASE),
        ],
    )
    found = recent.last_episode("tt0000009", path)
    assert found is not None
    season, episode, state = found
    assert (season, episode, state.last_played) == (1, 2, "2026-03-01 10:00:00")
    assert recent.recent(path) == [("episode", "tt0000009", 1, 2)]


def test_last_episode_of_a_half_watched_one_without_last_played_uses_the_bookmark(tmp_path):
    path = make_db(tmp_path, [(EP.format(3, 4), "", NOKTURNO_BASE, 0)], bookmarks={EP.format(3, 4): (600.0, 2400.0)})
    found = recent.last_episode("tt0000009", path)
    assert found is not None
    season, episode, state = found
    assert (season, episode, state.resume_seconds, state.play_count) == (3, 4, 600.0, 0)


def test_last_episode_is_per_series_and_ignores_other_shows_and_movies(tmp_path):
    path = make_db(
        tmp_path,
        [
            (EP.format(1, 1), "2026-01-01 10:00:00", NOKTURNO_BASE),
            (EP_OTHER.format(7, 7), "2026-05-01 10:00:00", NOKTURNO_BASE),  # newer, but another show
            (MOVIE, "2026-06-01 10:00:00", NOKTURNO_BASE),
        ],
    )
    first, second = recent.last_episode("tt0000009", path), recent.last_episode("tt0000008", path)
    assert first is not None and first[:2] == (1, 1)
    assert second is not None and second[:2] == (7, 7)
    assert recent.last_episode("tt0000001", path) is None  # a movie is not an episode
    assert recent.last_episode("tt0000005", path) is None


def test_several_series_and_movies_each_appear_once_with_their_own_state(tmp_path):
    path = make_db(
        tmp_path,
        [
            (EP.format(1, 1), "2026-01-01 10:00:00", NOKTURNO_BASE),
            (EP_OTHER.format(2, 3), "2026-04-01 10:00:00", NOKTURNO_BASE),
            (EP.format(1, 2), "2026-03-01 10:00:00", NOKTURNO_BASE),
            (MOVIE, "2026-02-01 10:00:00", NOKTURNO_BASE),
        ],
    )
    assert [entry for entry, _state in recent.recent_with_state(path)] == [
        ("episode", "tt0000008", 2, 3),
        ("episode", "tt0000009", 1, 2),
        ("movie", "tt0000001"),
    ]


def test_missing_or_broken_database_gives_nothing(tmp_path):
    bad = tmp_path / "broken.db"
    bad.write_text("not a database")
    assert recent.recent_with_state(str(bad)) == [] and recent.last_episode("tt0000009", str(bad)) is None
    assert recent.recent_with_state(str(tmp_path / "missing.db")) == []
    assert recent.last_episode("tt0000009", str(tmp_path / "missing.db")) is None


def test_no_database_path_at_all_gives_nothing(monkeypatch):
    monkeypatch.setattr(recent.watched, "db_path", lambda: None)
    assert recent.recent_with_state() == [] and recent.last_episode("tt0000009") is None
