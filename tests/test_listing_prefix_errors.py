# tests/test_listing_prefix_errors.py
"""Prefix screens: bad parameters, ApiError handling without a crash, and the Catalog requests they rely on."""

import pytest

from resources.lib import api
from tests.listing_support import labels, run

END_FAILED = {"handle": 7, "succeeded": False, "update": False, "cache": True}


def test_malformed_children_are_ignored(ui, cat):
    cat.data["prefixes"] = {
        "a": {
            "total": 500,
            "exact": "x",
            "children": [
                {"prefix": "ab", "n": 10},
                {"prefix": "../", "n": 1},
                {"prefix": "b", "n": 4},
                {"prefix": "ac"},
                "junk",
            ],
        }
    }
    run("?action=prefix&kind=movie&prefix=A")
    assert labels(ui) == ["AB (10)", "AC (0)"]
    assert cat.calls == [("prefixes", "movie", "a")]


@pytest.mark.parametrize(
    "query",
    [
        "?action=prefix&kind=bogus&prefix=a",
        "?action=prefix&kind=movie&prefix=a%20b",
        "?action=prefix&kind=movie&prefix=abcdefghijk",
        "?action=titles&kind=movie&prefix=../x",
    ],
)
def test_bad_parameters_fail_quietly_without_catalog_call(ui, cat, query):
    run(query)
    assert cat.calls == []
    assert ui.ended == [END_FAILED]


def test_api_error_on_prefixes_does_not_crash(ui, cat):
    cat.data["prefixes"] = api.ApiError(api.NETWORK)
    run("?action=prefix&kind=movie&prefix=a")
    assert ui.ended == [END_FAILED] and ui.added == []
    assert [d[0] for d in ui.dialogs] == ["notification"]


def test_api_error_on_titles_does_not_crash(ui, cat):
    cat.data["prefixes"] = {"ar": {"total": 5, "exact": 0, "children": []}}
    cat.data["titles"] = api.ApiError(api.SERVER, "500")
    run("?action=prefix&kind=movie&prefix=ar")
    assert ui.ended == [END_FAILED] and ui.added == []


def test_catalog_builds_prefix_requests(monkeypatch):
    calls = []
    monkeypatch.setattr(api, "fetch", lambda base, token, path, params=None, **kw: calls.append((path, params)) or {})
    catalog = api.Catalog("http://h:8090", "tok", "cs")
    catalog.prefixes("series", "ar")
    catalog.titles("movie", None, "name", 1, 100, "ar", True)
    catalog.titles("movie", None, "name", 2, 100, "ar")
    catalog.titles("movie", "K", "name", 1, 100)
    assert calls[0] == ("/v1/prefixes", {"type": "series", "prefix": "ar"})
    assert calls[1][1] == {
        "type": "movie",
        "letter": None,
        "sort": "name",
        "page": 1,
        "per_page": 100,
        "lang": "cs",
        "prefix": "ar",
        "exact": 1,
    }
    assert calls[2][1]["exact"] is None and calls[2][1]["prefix"] == "ar"
    assert "prefix" not in calls[3][1] and calls[3][1]["letter"] == "K"
