# tests/test_listing_genre.py
"""Genre folders, flat 'best rated' lists, the Czech/Slovak menu and the filters carried through the prefix drill-down."""

import pytest
import xbmcaddon

from resources.lib import api, const
from tests.listing_support import BASE, labels, movie, run
from tests.test_resources import PO_FILES, parse_po

END_FAILED = {"handle": 7, "succeeded": False, "update": False, "cache": True}
GENRES = [
    {"genre": "Drama", "n": 13349},
    {"genre": "Reality-TV", "n": 2284},
    {"genre": "Sci-Fi", "n": 835},
    {"genre": "Game-Show", "n": 892},
    {"genre": "News", "n": 312},
    {"genre": "Short", "n": 301},
    {"genre": "Talk-Show", "n": 766},
    {"genre": "Film-Noir", "n": 9},
]


def paths(ui):
    return [path for path, _item, _folder in ui.entries()]


def answer(prefix, total, exact, children):
    return {"prefix": prefix, "total": total, "exact": exact, "children": [{"prefix": p, "n": n} for p, n in children]}


@pytest.fixture
def czech(monkeypatch):
    """Kodi answers getLocalizedString from the Czech strings.po."""
    _, entries, _ = parse_po(PO_FILES["cs_cz"])

    class CzechAddon:
        def getLocalizedString(self, string_id):
            return entries[string_id][1]

    monkeypatch.setattr(xbmcaddon, "Addon", CzechAddon)


def test_genres_hide_noise_and_show_label_with_count(ui, cat):
    cat.data["genres"] = GENRES
    run("?action=genres&kind=series")
    assert labels(ui) == ["Drama (13349)", "Sci-Fi (835)", "Film-Noir (9)"]
    assert paths(ui)[0] == BASE + "?action=flat&kind=series&genre=Drama&page=1"
    assert paths(ui)[2] == BASE + "?action=flat&kind=series&genre=Film-Noir&page=1"
    assert cat.calls == [("genres", "series", False)]
    assert ui.content == ["files"]


def test_genres_use_czech_names_with_diacritics(ui, cat, czech):
    cat.data["genres"] = [{"genre": "Action", "n": 5}, {"genre": "Biography", "n": 4}, {"genre": "War", "n": 3}]
    run("?action=genres&kind=movie")
    assert labels(ui) == ["Akční (5)", "Životopisný (4)", "Válečný (3)"]


def test_unknown_genre_falls_back_to_its_imdb_name(ui, cat, czech):
    cat.data["genres"] = [{"genre": "Adult", "n": 2}]
    run("?action=genres&kind=movie")
    assert labels(ui) == ["Adult (2)"]


def test_malformed_genres_are_skipped(ui, cat):
    cat.data["genres"] = [{"genre": "../x", "n": 1}, "junk", {"n": 3}, {"genre": "Comedy"}]
    run("?action=genres&kind=movie")
    assert labels(ui) == ["Comedy (0)"]


def test_genres_of_czsk_ask_for_the_origin_and_keep_it_in_the_folder_urls(ui, cat):
    cat.data["genres"] = [{"genre": "Crime", "n": 7}]
    run("?action=genres&kind=series&origin=1")
    assert cat.calls == [("genres", "series", True)]
    assert paths(ui) == [BASE + "?action=flat&kind=series&genre=Crime&page=1&origin=1"]


def test_only_noise_genres_show_the_empty_notice(ui, cat):
    cat.data["genres"] = [{"genre": "News", "n": 1}]
    run("?action=genres&kind=movie")
    assert ui.entries() == []
    assert ("notification", "Nothing found.", "info") in ui.dialogs


def test_genres_api_error_is_reported_without_a_crash(ui, cat):
    cat.data["genres"] = api.ApiError(api.NETWORK)
    run("?action=genres&kind=movie")
    assert ui.ended == [END_FAILED] and ui.added == []


def test_flat_list_opens_sorted_by_rating(ui, cat):
    cat.data["titles"] = {"has_more": True, "items": [movie(1)]}
    run("?action=flat&kind=movie&page=1")
    assert cat.calls == [("titles", "movie", None, "rating", 1, 100, None, False, None, False, True)]
    assert labels(ui)[:2] == ["By rating -> By votes", "Movie 1 (2000)"]
    assert paths(ui)[0] == BASE + "?action=flat&kind=movie&sort=votes&page=1"
    assert paths(ui)[-1] == BASE + "?action=flat&kind=movie&sort=rating&page=2"
    assert ui.content == ["movies"]


@pytest.mark.parametrize(
    "sort, following", [("rating", "votes"), ("votes", "year"), ("year", "name"), ("name", "rating")]
)
def test_flat_sort_cycles_rating_votes_year_name(ui, cat, sort, following):
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run(f"?action=flat&kind=series&genre=Sci-Fi&sort={sort}")
    assert cat.calls[0][3] == sort
    assert paths(ui)[0] == BASE + f"?action=flat&kind=series&genre=Sci-Fi&sort={following}&page=1"


def test_flat_unknown_sort_uses_rating(ui, cat):
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=flat&kind=movie&sort=bogus")
    assert cat.calls[0][3] == "rating"


def test_flat_genre_passes_the_genre_and_keeps_it_when_paging(ui, cat):
    cat.data["titles"] = {"has_more": True, "items": [movie(1)]}
    run("?action=flat&kind=series&genre=Sci-Fi&origin=1&sort=year&page=2")
    assert cat.calls == [("titles", "series", None, "year", 2, 100, None, False, "Sci-Fi", True, True)]
    entries = paths(ui)
    assert len(entries) == 2  # no sort switch on page two
    assert entries[-1] == BASE + "?action=flat&kind=series&genre=Sci-Fi&origin=1&sort=year&page=3"
    assert ui.ended[-1]["update"] is True


def test_flat_empty_result_notifies_nothing_found(ui, cat):
    # a catalog that does not flag Czech/Slovak films yet answers total 0 for movies
    cat.data["titles"] = {"page": 1, "per_page": 100, "has_more": False, "total": 0, "items": []}
    run("?action=flat&kind=movie&origin=1&sort=rating&page=1")
    assert ("notification", "Nothing found.", "info") in ui.dialogs
    assert ui.ended[-1]["succeeded"] is True


def test_flat_respects_the_per_page_setting(ui, cat, monkeypatch):
    from resources.lib import cfg

    monkeypatch.setattr(cfg, "per_page", lambda: 40)
    cat.data["titles"] = {"has_more": False, "items": []}
    run("?action=flat&kind=movie")
    assert cat.calls[0][5] == 40


def test_flat_api_error_does_not_crash(ui, cat):
    cat.data["titles"] = api.ApiError(api.SERVER, "400")
    run("?action=flat&kind=movie&genre=Drama")
    assert ui.ended == [END_FAILED] and ui.added == []


@pytest.mark.parametrize(
    "query",
    ["?action=flat&kind=bogus", "?action=flat&kind=movie&genre=a%26b", "?action=genres&kind=x", "?action=czsk&kind=x"],
)
def test_bad_filter_parameters_fail_quietly(ui, cat, query):
    run(query)
    assert cat.calls == []
    assert ui.ended == [END_FAILED]


def test_czsk_menu_entries(ui, cat):
    run("?action=czsk&kind=series")
    assert labels(ui) == ["Best rated", "Most votes", "Newest", "A-Z", "Genres"]
    assert paths(ui) == [
        BASE + "?action=flat&kind=series&origin=1&sort=rating&page=1",
        BASE + "?action=flat&kind=series&origin=1&sort=votes&page=1",
        BASE + "?action=flat&kind=series&origin=1&sort=year&page=1",
        BASE + "?action=prefix&kind=series&origin=1",
        BASE + "?action=genres&kind=series&origin=1",
    ]
    assert cat.calls == []


def test_czsk_menu_is_czech_when_kodi_is(ui, cat, czech):
    run("?action=czsk&kind=movie")
    assert labels(ui) == ["Nejlépe hodnocené", "Nejvíce hlasů", "Nejnovější", "A-Z", "Žánry"]


def test_genre_strings_cover_22_genres_in_both_languages():
    assert len(const.GENRE_STRINGS) == 22
    assert sorted(const.GENRE_STRINGS.values()) == list(range(30100, 30122))
    assert not set(const.GENRE_STRINGS) & set(const.NOISE_GENRES)
    _, cs, _ = parse_po(PO_FILES["cs_cz"])
    _, en, _ = parse_po(PO_FILES["en_gb"])
    for name, string_id in const.GENRE_STRINGS.items():
        assert en[string_id][1] == name
    assert cs[const.GENRE_STRINGS["Action"]][1] == "Akční"
    assert cs[const.GENRE_STRINGS["Animation"]][1] == "Animovaný"
    assert cs[const.S_BEST_RATED][1] == "Nejlépe hodnocené"
    assert cs[const.S_CZSK][1] == "České a slovenské"
