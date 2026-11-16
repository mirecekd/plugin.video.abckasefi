# tests/test_title_masks.py
"""Year and rating in title lists: movie, series and mixed lists pass Kodi the label masks, folder menus keep the default."""

import pytest
import xbmcplugin

from resources.lib import listing_common
from tests.listing_support import movie, run, series

MASKS = [{"labelMask": "%T[ (%Y)]", "label2Mask": "%R"}]


def test_movie_titles_list_uses_the_year_and_rating_masks(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(1), movie(2)]}
    run("?action=titles&kind=movie&letter=K&sort=name")
    assert ui.sorts == [xbmcplugin.SORT_METHOD_NONE]
    assert ui.sort_masks == MASKS


def test_prefix_titles_screen_uses_the_masks(ui, cat):
    cat.data["prefixes"] = {"ar": {"prefix": "ar", "total": 100, "exact": 0, "children": []}}
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=prefix&kind=movie&prefix=ar")
    assert ui.content == ["movies"] and ui.sort_masks == MASKS


def test_mixed_search_result_uses_the_masks(ui, cat):
    ui.input_answer = "x"
    cat.data["search"] = {"items": [movie(1), series(2)]}
    run("?action=search")
    assert ui.content == ["videos"] and ui.sort_masks == MASKS


def test_series_only_list_uses_the_masks(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [series(1), series(2)]}
    run("?action=titles&kind=series&letter=K&sort=name")
    assert ui.content == ["tvshows"]
    assert ui.sort_masks == MASKS


def test_flat_genre_list_uses_the_masks(ui, cat):
    cat.data["titles"] = {"has_more": True, "items": [movie(1)]}
    run("?action=flat&kind=movie&genre=Drama&page=1")
    assert ui.content == ["movies"] and ui.sort_masks == MASKS


def test_series_flat_genre_list_uses_the_masks(ui, cat):
    cat.data["titles"] = {"has_more": True, "items": [series(1)]}
    run("?action=flat&kind=series&genre=Drama&page=1")
    assert ui.content == ["tvshows"] and ui.sort_masks == MASKS


def test_series_tmdb_list_uses_the_masks(ui, cat):
    cat.data["tmdb_list"] = {"has_more": False, "items": [series(1)]}
    run("?action=tmdb_list&kind=series&key=top&page=1")
    assert ui.content == ["tvshows"] and ui.sort_masks == MASKS


def test_tmdb_list_uses_the_masks(ui, cat):
    cat.data["tmdb_list"] = {"has_more": False, "items": [movie(1)]}
    run("?action=tmdb_list&kind=movie&key=top&page=1")
    assert ui.sort_masks == MASKS


@pytest.mark.parametrize("content", ["movies", "tvshows", "videos"])
def test_show_titles_passes_both_masks(ui, content):
    listing_common.show_titles(7, [], content)
    assert ui.sort_masks == MASKS


@pytest.mark.parametrize("content", ["files", "seasons", "episodes"])
def test_show_titles_leaves_other_content_unmasked(ui, content):
    listing_common.show_titles(7, [], content)
    assert ui.sort_masks == [{}]


def test_the_label_still_carries_the_year_as_fallback(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=titles&kind=movie&letter=K&sort=name")
    assert [item.getLabel() for _p, item, _f in ui.entries()][-1] == "Movie 1 (2000)"
