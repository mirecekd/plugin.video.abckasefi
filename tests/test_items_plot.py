# tests/test_items_plot.py
"""Plot from list answers: setPlot is called for movies and series only when `overview` is not empty."""

import pytest

from resources.lib import items, recent
from tests.listing_support import BASE, FakeCatalog, movie, run, series


def _tag(built):
    return built[1].tag


@pytest.mark.parametrize(("make", "build"), [(movie, items.movie_item), (series, items.series_item)])
def test_set_plot_with_overview(ui, make, build):
    built = build(dict(make(1), overview="A plot.", overview_lang="en"), FakeCatalog())
    assert _tag(built).calls["setPlot"] == ("A plot.",)


@pytest.mark.parametrize(("make", "build"), [(movie, items.movie_item), (series, items.series_item)])
@pytest.mark.parametrize("overview", ["", None])
def test_no_set_plot_without_overview(ui, make, build, overview):
    assert "setPlot" not in _tag(build(dict(make(1), overview=overview), FakeCatalog())).calls
    assert "setPlot" not in _tag(build(make(1), FakeCatalog())).calls


def test_titles_list_sets_plot_only_where_present(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [dict(movie(1), overview="One"), dict(movie(2), overview="")]}
    run("?action=titles&kind=movie&letter=K&page=2")
    first, second = (item for _p, item, _f in ui.entries())
    assert first.tag.calls["setPlot"] == ("One",)
    assert "setPlot" not in second.tag.calls


def test_search_and_tmdb_list_set_plot(ui, cat):
    ui.input_answer = "x"
    cat.data["search"] = {"items": [dict(movie(1), overview="Found"), dict(series(2), overview="Show plot")]}
    run("?action=search")
    assert [item.tag.calls.get("setPlot") for _p, item, _f in ui.entries()] == [("Found",), ("Show plot",)]
    ui.added.clear()
    cat.data["tmdb_list"] = {"has_more": False, "items": [dict(series(3), overview="Listed")]}
    run("?action=tmdb_list&kind=series&key=pop&page=2")
    assert ui.entries()[0][1].tag.calls["setPlot"] == ("Listed",)
    assert ui.entries()[0][0] == BASE + "?action=seasons&id=tt0000003"


def test_recently_watched_movie_gets_plot(ui, cat, monkeypatch):
    monkeypatch.setattr(recent, "recent", lambda: [("movie", "tt0000001")])
    cat.data["title"] = {"title": "M", "overview": "Seen plot"}
    run("?action=recent")
    assert ui.entries()[0][1].tag.calls["setPlot"] == ("Seen plot",)
