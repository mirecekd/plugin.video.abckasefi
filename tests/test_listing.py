# tests/test_listing.py
"""Screens: root menu, letters, paging and chunks, item paths, search, lists, seasons and episodes."""

import xbmcplugin

from resources.lib import listing_common, urls, watched
from tests.listing_support import BASE, labels, movie, run, series


def test_root_menu_entries(ui, cat):
    run("")
    entries = ui.entries()
    assert [path for path, _i, _f in entries] == [
        BASE + "?action=kind&kind=movie",
        BASE + "?action=kind&kind=series",
        BASE + "?action=search",
        BASE + "?action=lists",
        BASE + "?action=recent",
        BASE + "?action=settings",
    ]
    assert all(is_folder for _p, _i, is_folder in entries)
    assert labels(ui) == ["Movies", "Series", "Search", "TMDB lists", "Recently watched", "Settings"]
    assert ui.ended == [{"handle": 7, "succeeded": True, "update": False, "cache": False}]


def test_kind_menu_has_recent_letters_lists_and_search(ui, cat):
    run("?action=kind&kind=series")
    assert [p for p, _i, _f in ui.entries()] == [
        BASE + "?action=recent&kind=series",
        BASE + "?action=letters&kind=series",
        BASE + "?action=lists&kind=series",
        BASE + "?action=search&kind=series",
    ]


def test_letters_show_counts_a_to_z_then_digits(ui, cat):
    cat.data["letters"] = [{"letter": "0-9", "n": 5}, {"letter": "B", "n": 12}, {"letter": "A", "n": 3}]
    run("?action=letters&kind=movie")
    assert labels(ui) == ["A (3)", "B (12)", "0-9 (5)"]
    assert ui.entries()[0][0] == BASE + "?action=prefix&kind=movie&prefix=a"
    assert ui.entries()[2][0] == BASE + "?action=prefix&kind=movie&prefix=&digits=1"
    assert cat.calls == [("letters", "movie")]


def test_titles_page_one_has_sort_selector_and_next_page(ui, cat):
    cat.data["titles"] = {"has_more": True, "items": [movie(1), movie(2)]}
    run("?action=titles&kind=movie&letter=K")
    entries = ui.entries()
    assert cat.calls[0][:5] == ("titles", "movie", "K", "name", 1)
    assert entries[0][0] == BASE + "?action=titles&kind=movie&letter=K&sort=rating&page=1"
    assert entries[-1][0] == BASE + "?action=titles&kind=movie&letter=K&sort=name&page=2"
    assert labels(ui)[-1] == "Next page"
    assert len(entries) == 1 + 2 + 1
    assert ui.ended[-1]["update"] is False and ui.ended[-1]["cache"] is False
    assert ui.content == ["movies"] and ui.sorts == [xbmcplugin.SORT_METHOD_NONE]


def test_titles_page_two_updates_listing_without_sort_item(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(3)]}
    run("?action=titles&kind=movie&letter=K&sort=year&page=2")
    assert cat.calls[0][3:5] == ("year", 2)
    assert ui.ended[-1]["update"] is True
    assert len(ui.entries()) == 1 and "Next page" not in labels(ui)


def test_titles_split_into_chunks_of_200(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(n) for n in range(1, 451)]}
    run("?action=titles&kind=movie&letter=K&page=2")
    assert [len(batch) for batch in ui.added] == [200, 200, 50]
    assert listing_common.CHUNK == 200


def test_series_titles_are_folders_to_seasons(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [series(5)]}
    run("?action=titles&kind=series&letter=S&page=2")
    path, _item, is_folder = ui.entries()[0]
    assert path == BASE + "?action=seasons&id=tt0000005" and is_folder
    assert ui.content == ["tvshows"]


def test_movie_item_path_is_nokturno_url_playable_not_folder(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(68646)]}
    run("?action=titles&kind=movie&letter=G&page=2")
    path, item, is_folder = ui.entries()[0]
    assert path == urls.nokturno_movie_url("tt0068646")
    assert path.encode() == b"plugin://plugin.video.nokturno/?action=play&type=movie&id=tt0068646&ask=1"
    assert is_folder is False
    assert item.getProperty("IsPlayable") == "true"
    assert "setPlaycount" not in item.tag.calls


def test_malformed_item_is_skipped_not_fatal(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [{"id": "bad", "title": "x"}, movie(1)]}
    run("?action=titles&kind=movie&letter=G&page=2")
    assert len(ui.entries()) == 1 and ui.ended[-1]["succeeded"] is True


def test_search_with_empty_input_does_nothing(ui, cat):
    ui.input_answer = "   "
    run("?action=search")
    assert cat.calls == [] and ui.added == []
    assert [d[0] for d in ui.dialogs] == ["input"]
    assert ui.ended == [{"handle": 7, "succeeded": False, "update": False, "cache": True}]


def test_search_lists_mixed_results(ui, cat):
    ui.input_answer = "matrix"
    cat.data["search"] = {"has_more": False, "items": [movie(1), series(2)]}
    run("?action=search")
    assert cat.calls[0][:3] == ("search", "matrix", None)
    assert [f for _p, _i, f in ui.entries()] == [False, True]
    assert ui.content == ["videos"]


def test_lists_folders_for_one_kind(ui, cat):
    cat.data["lists"] = {"movie": {"top": "Top rated"}, "series": {"pop": "Popular"}}
    run("?action=lists&kind=series")
    assert labels(ui) == ["Popular"]
    assert ui.entries()[0][0] == BASE + "?action=tmdb_list&kind=series&key=pop&page=1"


def test_tmdb_list_paging(ui, cat):
    cat.data["tmdb_list"] = {"has_more": True, "items": [movie(1)]}
    run("?action=tmdb_list&kind=movie&key=top&page=3")
    assert cat.calls[0][:4] == ("tmdb_list", "movie", "top", 3)
    assert ui.entries()[-1][0] == BASE + "?action=tmdb_list&kind=movie&key=top&sort=tmdb&page=4"
    assert ui.ended[-1]["update"] is True


def test_seasons_note_shows_notification_and_progress(ui, cat, monkeypatch):
    cat.data["seasons"] = {
        "note": "Data are incomplete",
        "seasons": [{"season": 0, "name": "", "episodes": 2}, {"season": 1, "name": "", "episodes": 2}],
    }
    monkeypatch.setattr(watched, "load", lambda path=None: {"tt0000009": {1: {1: 1, 2: 1}}})
    run("?action=seasons&id=tt0000009")
    assert ("notification", "Data are incomplete", "info") in ui.dialogs
    assert labels(ui) == ["Specials", "Season 1"]
    assert ui.entries()[1][0] == BASE + "?action=episodes&id=tt0000009&season=1"
    entry = ui.entries()[1][1]
    assert entry.getProperty("WatchedEpisodes") == "2" and entry.getProperty("TotalEpisodes") == "2"
    assert entry.tag.calls["setPlaycount"] == (1,)
    assert ui.entries()[0][1].tag.calls["setPlaycount"] == (0,)


def test_episodes_use_nokturno_url_and_series_title(ui, cat):
    cat.data["episodes"] = {"episodes": [{"episode": 2, "name": "B"}, {"episode": 1, "name": "A"}]}
    cat.data["title"] = {"title": "Show"}
    run("?action=episodes&id=tt0000009&season=1")
    paths = [p for p, _i, _f in ui.entries()]
    assert paths == [urls.nokturno_episode_url("tt0000009", 1, 1), urls.nokturno_episode_url("tt0000009", 1, 2)]
    assert not any(f for _p, _i, f in ui.entries())
    assert ui.entries()[0][1].tag.calls["setTvShowTitle"] == ("Show",)
    assert ui.content == ["episodes"]
