# tests/test_listing_watched.py
"""Series folders in title lists get a watched mark from the remembered season sizes (totals.py + Kodi's database)."""
from resources.lib import totals, watched
from tests.listing_support import run, series


def _series_entry(ui, cat, monkeypatch, known, state):
    cat.data["titles"] = {"has_more": False, "items": [series(5)]}
    monkeypatch.setattr(totals, "load", lambda path=None: known)
    monkeypatch.setattr(watched, "load", lambda path=None: state)
    run("?action=titles&kind=series&letter=S&page=2")
    return ui.entries()[0][1]


def test_fully_watched_series_folder_is_marked_watched(ui, cat, monkeypatch):
    # regression (review P1): series folders in title lists never received a watched mark
    entry = _series_entry(ui, cat, monkeypatch, {"tt0000005": {0: 1, 1: 2, 2: 1}},
                          {"tt0000005": {1: {1: 1, 2: 1}, 2: {1: 3}}})
    assert entry.tag.calls["setPlaycount"] == (1,)
    assert (entry.getProperty("WatchedEpisodes"), entry.getProperty("TotalEpisodes")) == ("3", "3")  # specials not counted


def test_partly_watched_series_folder_is_not_marked(ui, cat, monkeypatch):
    entry = _series_entry(ui, cat, monkeypatch, {"tt0000005": {1: 2, 2: 2}},
                          {"tt0000005": {1: {1: 1, 2: 1}, 2: {1: 1}}})
    assert entry.tag.calls["setPlaycount"] == (0,)
    assert (entry.getProperty("WatchedEpisodes"), entry.getProperty("TotalEpisodes")) == ("3", "4")


def test_series_with_unknown_size_gets_no_mark_rather_than_a_wrong_one(ui, cat, monkeypatch):
    entry = _series_entry(ui, cat, monkeypatch, {}, {"tt0000005": {1: {1: 1}}})
    assert "setPlaycount" not in entry.tag.calls and entry.getProperty("TotalEpisodes") == ""


def test_opening_a_series_remembers_its_season_sizes(ui, cat, monkeypatch):
    saved = []
    monkeypatch.setattr(totals, "save", lambda tt, counts, path=None: saved.append((tt, counts)))
    monkeypatch.setattr(watched, "load", lambda path=None: {})
    cat.data["seasons"] = {"seasons": [{"season": 0, "episodes": 1}, {"season": 1, "episodes": 8}]}
    run("?action=seasons&id=tt0000009")
    assert saved == [("tt0000009", {0: 1, 1: 8})]
