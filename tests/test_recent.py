# tests/test_recent.py
"""Recently watched: rows read from a real (temporary) MyVideos-like sqlite file, parsed and listed newest first."""

import pytest

from resources.lib import api, recent
from resources.lib.const import NOKTURNO_BASE
from tests.listing_support import BASE, labels, run
from tests.recent_support import EP, MOVIE, OTHER, make_db


def test_parse_movie_and_episode_urls():
    assert recent.parse(MOVIE) == ("movie", "tt0000001")
    assert recent.parse(EP.format(2, 5)) == ("episode", "tt0000009", 2, 5)
    assert recent.parse(NOKTURNO_BASE + "?action=seasons&id=tt0000009") is None
    assert recent.parse("") is None and recent.parse(None) is None


def test_newest_first_one_entry_per_series(tmp_path):
    path = make_db(
        tmp_path,
        [
            (MOVIE, "2026-01-01 10:00:00", NOKTURNO_BASE),
            (EP.format(1, 1), "2026-02-01 10:00:00", NOKTURNO_BASE),
            (EP.format(1, 2), "2026-03-01 10:00:00", NOKTURNO_BASE),  # the later episode of the same show wins
            (OTHER, "2026-02-15 10:00:00", NOKTURNO_BASE),
        ],
    )
    assert recent.recent(path) == [("episode", "tt0000009", 1, 2), ("movie", "tt0000002"), ("movie", "tt0000001")]


def test_resume_point_without_last_played_counts_and_foreign_rows_do_not(tmp_path):
    path = make_db(
        tmp_path,
        [
            (MOVIE, "", NOKTURNO_BASE),  # stopped half way: only a bookmark
            (OTHER, "", NOKTURNO_BASE),  # never played, no bookmark: not recent
            ("/movies/x.mkv", "2026-05-01 10:00:00", "/movies/"),
        ],
        bookmarks=(MOVIE,),
    )
    assert recent.recent(path) == [("movie", "tt0000001")]


def test_limit_and_unreadable_database(tmp_path):
    rows = [
        (NOKTURNO_BASE + f"?action=play&type=movie&id=tt{n:07d}&ask=1", f"2026-01-{n:02d} 10:00:00", NOKTURNO_BASE)
        for n in range(1, 11)
    ]
    assert len(recent.recent(make_db(tmp_path, rows), limit=4)) == 4
    bad = tmp_path / "broken.db"
    bad.write_text("not a database")
    assert recent.recent(str(bad)) == []
    assert recent.recent(str(tmp_path / "missing.db")) == []


@pytest.fixture
def stored(monkeypatch):
    def put(entries):
        monkeypatch.setattr(recent, "recent", lambda *a, **k: entries)

    return put


def test_recent_screen_lists_movie_and_series_folder_entries(ui, cat, stored):
    stored([("episode", "tt0000009", 2, 3), ("movie", "tt0000001")])
    cat.data["title"] = {"title": "Name", "year": 1999, "type": "movie"}
    run("?action=recent")
    entries = ui.entries()
    assert entries[0][0] == BASE + "?action=resume&id=tt0000009" and entries[0][2] is True
    assert entries[1][0] == MOVIE and entries[1][2] is False
    assert labels(ui) == ["Name (S02E03)", "Name (1999)"]
    assert ui.content == ["videos"]


def test_recent_screen_survives_a_title_the_catalog_does_not_know(ui, cat, stored):
    stored([("movie", "tt0000001")])
    cat.data["title"] = api.ApiError(api.SERVER, "404")
    run("?action=recent")
    assert labels(ui) == ["tt0000001"] and ui.entries()[0][0] == MOVIE


def test_recent_screen_empty_says_nothing_found(ui, cat, stored):
    stored([])
    run("?action=recent")
    assert ui.entries() == [] and any(d[0] == "notification" and "Nothing found" in d[1] for d in ui.dialogs)


def test_recent_screen_reports_a_refused_token_once(ui, cat, stored):
    stored([("movie", "tt0000001"), ("movie", "tt0000002")])
    cat.data["title"] = api.ApiError(api.AUTH)
    run("?action=recent")
    assert sum(1 for d in ui.dialogs if d[0] == "notification" and "refused the token" in d[1]) == 1


def test_root_menu_offers_recently_watched(ui, cat):
    run("")
    assert BASE + "?action=recent" in [path for path, _i, _f in ui.entries()]
    assert "Recently watched" in labels(ui)
