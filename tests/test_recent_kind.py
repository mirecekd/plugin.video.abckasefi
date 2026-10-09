# tests/test_recent_kind.py
"""Recently watched by kind: the Movies / Series menus, the kind filter applied before the item limit, the screens."""

import pytest

from resources.lib import recent
from resources.lib.const import NOKTURNO_BASE
from tests.listing_support import BASE, labels, run
from tests.recent_support import EP, MOVIE, OTHER, make_db


def _series_rows(count):
    """One episode row per distinct series tt1000000+, newer than every movie row below."""
    return [
        (
            NOKTURNO_BASE + f"?action=play&type=series&id=tt{n:07d}%3A1%3A1&series=tt{n:07d}&ask=1",
            f"2026-06-01 10:{n:02d}:00",
            NOKTURNO_BASE,
        )
        for n in range(1000000, 1000000 + count)
    ]


def _mixed_db(tmp_path):
    return make_db(
        tmp_path,
        [
            (MOVIE, "2026-01-01 10:00:00", NOKTURNO_BASE),
            (EP.format(2, 5), "2026-03-01 10:00:00", NOKTURNO_BASE),
            (OTHER, "2026-02-01 10:00:00", NOKTURNO_BASE),
        ],
    )


@pytest.mark.parametrize("kind", ["movie", "series"])
def test_kind_menu_starts_with_recent(ui, cat, kind):
    run(f"?action=kind&kind={kind}")
    paths = [p for p, _i, _f in ui.entries()]
    assert paths[0] == BASE + f"?action=recent&kind={kind}"
    assert paths[1:] == [
        BASE + f"?action=letters&kind={kind}",
        BASE + f"?action=lists&kind={kind}",
        BASE + f"?action=search&kind={kind}",
    ]
    assert labels(ui)[0] == "Recently watched"


def test_recent_filters_by_kind(tmp_path):
    path = _mixed_db(tmp_path)
    assert recent.recent(path, kind="movie") == [("movie", "tt0000002"), ("movie", "tt0000001")]
    assert recent.recent(path, kind="series") == [("episode", "tt0000009", 2, 5)]
    both = [("episode", "tt0000009", 2, 5), ("movie", "tt0000002"), ("movie", "tt0000001")]
    assert recent.recent(path) == both
    assert recent.recent(path, kind=None) == both
    assert [entry for entry, _state in recent.recent_with_state(path, kind="series")] == [
        ("episode", "tt0000009", 2, 5)
    ]


def test_limit_applies_after_the_kind_filter(tmp_path):
    rows = _series_rows(30) + [
        (MOVIE, "2026-01-01 10:00:00", NOKTURNO_BASE),
        (OTHER, "2026-01-02 10:00:00", NOKTURNO_BASE),
        (NOKTURNO_BASE + "?action=play&type=movie&id=tt0000003&ask=1", "2026-01-03 10:00:00", NOKTURNO_BASE),
    ]
    path = make_db(tmp_path, rows)
    assert len(recent.recent(path)) == recent.MAX_ITEMS  # unfiltered, the movies are pushed out by the series
    assert [entry[1] for entry in recent.recent(path, kind="movie")] == ["tt0000003", "tt0000002", "tt0000001"]
    assert len(recent.recent(path, kind="series")) == recent.MAX_ITEMS


def test_limit_applies_after_the_kind_filter_for_series(tmp_path):
    rows = [
        (NOKTURNO_BASE + f"?action=play&type=movie&id=tt{n:07d}&ask=1", f"2026-06-01 10:{n:02d}:00", NOKTURNO_BASE)
        for n in range(1, 41)
    ]
    rows.append((EP.format(1, 1), "2026-01-01 10:00:00", NOKTURNO_BASE))
    path = make_db(tmp_path, rows)
    assert recent.recent(path, kind="series") == [("episode", "tt0000009", 1, 1)]


@pytest.fixture
def stored(monkeypatch, tmp_path):
    path = _mixed_db(tmp_path)
    monkeypatch.setattr(recent.watched, "db_path", lambda: path)


def test_recent_movie_screen_has_only_playable_movies(ui, cat, stored):
    cat.data["title"] = {"title": "Name", "year": 1999, "type": "movie"}
    run("?action=recent&kind=movie")
    entries = ui.entries()
    assert [(p, is_folder) for p, _i, is_folder in entries] == [(OTHER, False), (MOVIE, False)]
    assert labels(ui) == ["Name (1999)", "Name (1999)"]


def test_recent_series_screen_has_only_resume_folders(ui, cat, stored):
    cat.data["title"] = {"title": "Show", "year": 2010, "type": "series"}
    run("?action=recent&kind=series")
    assert [(p, is_folder) for p, _i, is_folder in ui.entries()] == [(BASE + "?action=resume&id=tt0000009", True)]
    assert labels(ui) == ["Show (S02E05)"]


def test_recent_without_kind_shows_both(ui, cat, stored):
    cat.data["title"] = {"title": "Name", "year": 1999, "type": "movie"}
    run("?action=recent")
    assert [(p, f) for p, _i, f in ui.entries()] == [
        (BASE + "?action=resume&id=tt0000009", True),
        (OTHER, False),
        (MOVIE, False),
    ]


def test_recent_with_a_bad_kind_is_rejected(ui, cat, stored):
    run("?action=recent&kind=foo")
    assert ui.entries() == []
    assert cat.calls == []


def test_recent_with_nothing_of_that_kind_notifies(ui, cat, monkeypatch, tmp_path):
    path = make_db(tmp_path, [(MOVIE, "2026-01-01 10:00:00", NOKTURNO_BASE)])
    monkeypatch.setattr(recent.watched, "db_path", lambda: path)
    run("?action=recent&kind=series")
    assert ui.entries() == []
    assert ("notification", "Nothing found.", "info") in ui.dialogs
