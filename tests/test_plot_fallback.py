# tests/test_plot_fallback.py
"""Fallback plot for list items without an overview: genres and IMDb rating, never replacing a real overview."""

import pytest

from resources.lib import items
from resources.lib.plot_fallback import fallback_plot, votes_short
from tests.listing_support import FakeCatalog, movie, run, series

RATED = {"genres": ["Drama", "Crime"], "rating": 8.2, "votes": 2_900_000, "rating_reliable": True}


@pytest.mark.parametrize(
    ("votes", "text"),
    [
        (0, "0"),
        (850, "850"),
        (999, "999"),
        (1000, "1.0k"),
        (1234, "1.2k"),
        (999_949, "999.9k"),
        (999_950, "1.0M"),
        (2_900_000, "2.9M"),
    ],
)
def test_votes_are_compact_and_language_neutral(votes, text):
    assert votes_short(votes) == text


def test_genres_and_rating(ui):
    assert fallback_plot(RATED) == "Drama, Crime | IMDb 8.2 (2.9M)"


def test_genres_use_the_localized_names_when_kodi_has_them(ui, monkeypatch):
    monkeypatch.setattr("resources.lib.plot_fallback.texts.t", lambda string_id: f"#{string_id}")
    plot = fallback_plot({"genres": ["Drama", "Mystery-Unlisted"]})
    assert plot.endswith(", Mystery-Unlisted") and plot.startswith("#")


def test_no_rating_leaves_only_genres(ui):
    assert fallback_plot({"genres": ["Drama"]}) == "Drama"


def test_unreliable_rating_is_left_out(ui):
    assert fallback_plot(dict(RATED, rating_reliable=False)) == "Drama, Crime"


def test_rating_without_genres_or_votes(ui):
    assert fallback_plot({"rating": 7.04, "votes": 0}) == "IMDb 7.0"
    assert fallback_plot({"rating": 7.04, "votes": 1234}) == "IMDb 7.0 (1.2k)"


def test_nothing_available_gives_an_empty_text(ui):
    assert fallback_plot({}) == ""
    assert fallback_plot({"genres": [], "rating": None, "votes": None}) == ""
    assert fallback_plot({"rating": 8.0, "rating_reliable": False}) == ""


@pytest.mark.parametrize(("make", "build"), [(movie, items.movie_item), (series, items.series_item)])
def test_items_without_overview_get_the_fallback_plot(ui, make, build):
    built = build({**make(1), **RATED, "overview": ""}, FakeCatalog())
    assert built[1].tag.calls["setPlot"] == ("Drama, Crime | IMDb 8.2 (2.9M)",)


@pytest.mark.parametrize(("make", "build"), [(movie, items.movie_item), (series, items.series_item)])
def test_a_real_overview_is_used_unchanged(ui, make, build):
    built = build({**make(1), **RATED, "overview": "A plot."}, FakeCatalog())
    assert built[1].tag.calls["setPlot"] == ("A plot.",)


def test_listing_screen_uses_the_fallback_for_items_without_overview(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [{**movie(1), **RATED}, movie(2)]}
    run("?action=titles&kind=movie&letter=K&page=2")
    first, second = (item for _p, item, _f in ui.entries())
    assert first.tag.calls["setPlot"] == ("Drama, Crime | IMDb 8.2 (2.9M)",)
    assert "setPlot" not in second.tag.calls
