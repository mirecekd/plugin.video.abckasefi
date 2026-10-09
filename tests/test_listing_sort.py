# tests/test_listing_sort.py
"""Sort switchers: letter listings cycle name/rating/votes/year, TMDB lists cycle tmdb/rating/votes/year/name."""

import pytest

from tests.listing_support import BASE, labels, movie, run


def _first_sort(ui):
    return ui.entries()[0][0].split("sort=")[1].split("&")[0]


@pytest.mark.parametrize(
    "sort, following", [("name", "rating"), ("rating", "votes"), ("votes", "year"), ("year", "name")]
)
def test_titles_switch_cycles_name_rating_votes_year(ui, cat, sort, following):
    cat.data["titles"] = {"has_more": False, "items": []}
    run(f"?action=titles&kind=movie&letter=K&sort={sort}")
    assert cat.calls[0][3] == sort
    assert ui.entries()[0][0] == BASE + f"?action=titles&kind=movie&letter=K&sort={following}&page=1"


def test_titles_switch_label_shows_current_and_next(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": []}
    run("?action=titles&kind=movie&letter=K&sort=rating")
    assert labels(ui)[0] == "By rating -> By votes"


def test_titles_unknown_sort_uses_name(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=titles&kind=movie&letter=K&sort=bogus")
    assert cat.calls[0][3] == "name"
    assert _first_sort(ui) == "rating"


@pytest.mark.parametrize(
    "sort, following", [("tmdb", "rating"), ("rating", "votes"), ("votes", "year"), ("year", "name"), ("name", "tmdb")]
)
def test_tmdb_list_switch_cycles_all_five(ui, cat, sort, following):
    cat.data["tmdb_list"] = {"has_more": False, "items": [movie(1)]}
    run(f"?action=tmdb_list&kind=movie&key=top&sort={sort}")
    assert cat.calls[0] == ("tmdb_list", "movie", "top", 1, 100, sort)
    assert ui.entries()[0][0] == BASE + f"?action=tmdb_list&kind=movie&key=top&sort={following}&page=1"


def test_tmdb_list_switch_label_shows_current_and_next(ui, cat):
    cat.data["tmdb_list"] = {"has_more": False, "items": []}
    run("?action=tmdb_list&kind=movie&key=top")
    assert labels(ui)[0] == "TMDB order -> By rating"
    run("?action=tmdb_list&kind=movie&key=top&sort=name")
    assert labels(ui)[-1] == "By name -> TMDB order"


def test_tmdb_list_default_sort_is_tmdb(ui, cat):
    cat.data["tmdb_list"] = {"has_more": False, "items": []}
    run("?action=tmdb_list&kind=series&key=pop")
    assert cat.calls[0][5] == "tmdb"


def test_tmdb_list_unknown_sort_uses_tmdb(ui, cat):
    cat.data["tmdb_list"] = {"has_more": False, "items": []}
    run("?action=tmdb_list&kind=series&key=pop&sort=bogus")
    assert cat.calls[0][5] == "tmdb"
    assert _first_sort(ui) == "rating"


def test_tmdb_list_next_page_keeps_sort_and_has_no_switch(ui, cat):
    cat.data["tmdb_list"] = {"has_more": True, "items": [movie(1)]}
    run("?action=tmdb_list&kind=movie&key=top&sort=votes&page=2")
    assert cat.calls[0][3:] == (2, 100, "votes")
    entries = ui.entries()
    assert len(entries) == 2
    assert entries[-1][0] == BASE + "?action=tmdb_list&kind=movie&key=top&sort=votes&page=3"


def test_tmdb_list_first_page_next_keeps_sort(ui, cat):
    cat.data["tmdb_list"] = {"has_more": True, "items": [movie(1)]}
    run("?action=tmdb_list&kind=movie&key=top&sort=year")
    assert ui.entries()[-1][0] == BASE + "?action=tmdb_list&kind=movie&key=top&sort=year&page=2"


def test_titles_next_page_keeps_votes_sort(ui, cat):
    cat.data["titles"] = {"has_more": True, "items": [movie(1)]}
    run("?action=titles&kind=movie&letter=K&sort=votes")
    assert ui.entries()[-1][0] == BASE + "?action=titles&kind=movie&letter=K&sort=votes&page=2"
