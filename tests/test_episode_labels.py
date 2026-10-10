# tests/test_episode_labels.py
"""Episode numbers in the list: episodes() passes Kodi a label mask, every other screen keeps the default label."""

import pytest
import xbmcplugin

from resources.lib import listing_common, recent, totals
from resources.lib.const import NOKTURNO_BASE
from resources.lib.items import episode_item
from tests.listing_support import movie, run, series
from tests.recent_support import EP, make_db

TT = "tt0000009"


def test_episodes_screen_passes_the_number_and_title_mask(ui, cat):
    cat.data["episodes"] = {"episodes": [{"episode": 18, "name": "Name"}]}
    run(f"?action=episodes&id={TT}&season=1")
    assert ui.sorts == [xbmcplugin.SORT_METHOD_NONE]
    assert ui.sort_masks == [{"labelMask": "%H. %T", "label2Mask": ""}]


@pytest.fixture
def other_screens(tmp_path, monkeypatch, ui, cat):
    """Data for every screen except episodes, so each can be run with a bare query."""
    ui.input_answer = "matrix"
    page = {"has_more": False, "items": [movie(1), series(2)]}
    for name in ("titles", "search", "tmdb_list"):
        cat.data[name] = page
    cat.data["letters"] = [{"letter": "A", "n": 3}]
    cat.data["seasons"] = {"seasons": [{"season": 1, "name": "", "episodes": 2}]}
    cat.data["title"] = {"title": "Name", "year": 1999, "type": "movie"}
    monkeypatch.setattr(recent, "recent", lambda *a, **k: [("movie", "tt0000001")])
    row = (EP.format(1, 1), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)
    path = make_db(tmp_path, [row])
    monkeypatch.setattr(recent.watched, "db_path", lambda: path)
    monkeypatch.setattr(totals, "load", lambda path=None: {TT: {1: 4}})
    monkeypatch.setattr(totals, "save", lambda tt, data, path=None: None)


@pytest.mark.parametrize(
    "query",
    [
        "?action=letters&kind=movie",
        "?action=titles&kind=movie&letter=K&sort=name",
        "?action=seasons&id=" + TT,
        "?action=recent",
        "?action=resume&id=" + TT,
        "?action=search",
        "?action=tmdb_list&kind=movie&key=top&page=1",
    ],
)
def test_other_screens_add_the_sort_method_without_masks(ui, other_screens, query):
    run(query)
    assert ui.sorts == [xbmcplugin.SORT_METHOD_NONE]
    assert ui.sort_masks == [{}]


def test_show_without_label_mask_keeps_the_plain_call(ui):
    listing_common.show(7, [], "movies")
    assert ui.sorts == [xbmcplugin.SORT_METHOD_NONE] and ui.sort_masks == [{}]


def test_show_with_label_mask_forwards_both_masks(ui):
    listing_common.show(7, [], "episodes", label_mask="%H. %T", label2_mask="%D")
    assert ui.sort_masks == [{"labelMask": "%H. %T", "label2Mask": "%D"}]


def test_episode_item_sets_mediatype_season_and_episode(ui, cat):
    _path, item, folder = episode_item(TT, 2, {"episode": 18, "name": "Name"}, "Show", cat())
    calls = item.getVideoInfoTag().calls
    assert calls["setMediaType"] == ("episode",)
    assert calls["setSeason"] == (2,) and calls["setEpisode"] == (18,)
    assert folder is False


def test_episode_label_has_the_number_and_title_does_not(ui, cat):
    _path, item, _folder = episode_item(TT, 2, {"episode": 18, "name": "Name"}, "Show", cat())
    assert item.getLabel() == "18. Name"
    assert item.getVideoInfoTag().calls["setTitle"] == ("Name",)
