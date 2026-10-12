# tests/test_listing_genre_prefix.py
"""The prefix drill-down restricted to Czech/Slovak titles and/or a genre: the filters ride in every folder URL."""

from tests.listing_support import BASE, labels, movie, run


def paths(ui):
    return [path for path, _item, _folder in ui.entries()]


def answer(prefix, total, exact, children):
    return {"prefix": prefix, "total": total, "exact": exact, "children": [{"prefix": p, "n": n} for p, n in children]}


def test_prefix_drill_down_carries_origin_through_folders(ui, cat):
    cat.data["prefixes"] = {"": answer("", 803, 0, [("a", 32), ("p", 100)])}
    run("?action=prefix&kind=series&origin=1")
    assert labels(ui) == ["A (32)", "P (100)"]
    assert paths(ui) == [
        BASE + "?action=prefix&kind=series&prefix=a&origin=1",
        BASE + "?action=prefix&kind=series&prefix=p&origin=1",
    ]
    assert cat.calls == [("prefixes", "series", "", None, True)]


def test_prefix_exact_folder_and_titles_keep_genre_and_origin(ui, cat):
    cat.data["prefixes"] = {"ar": answer("ar", 500, 3, [("arm", 497)])}
    run("?action=prefix&kind=series&prefix=ar&genre=Comedy&origin=1")
    assert paths(ui)[0] == BASE + "?action=titles&kind=series&prefix=ar&exact=1&page=1&genre=Comedy&origin=1"
    assert paths(ui)[1] == BASE + "?action=prefix&kind=series&prefix=arm&genre=Comedy&origin=1"
    assert cat.calls == [("prefixes", "series", "ar", "Comedy", True)]
    ui.added.clear()
    cat.data["titles"] = {"has_more": True, "items": [movie(1)]}
    run("?action=titles&kind=series&prefix=ar&exact=1&genre=Comedy&origin=1&page=1")
    assert cat.calls[-1] == ("titles", "series", None, "name", 1, 100, "ar", True, "Comedy", True, False)
    assert paths(ui)[0] == BASE + "?action=titles&kind=series&prefix=ar&exact=1&genre=Comedy&origin=1&sort=rating&page=1"
    assert paths(ui)[-1] == BASE + "?action=titles&kind=series&prefix=ar&exact=1&genre=Comedy&origin=1&sort=name&page=2"


def test_prefix_listing_of_a_small_czsk_prefix_passes_the_filters(ui, cat):
    cat.data["prefixes"] = {"pat": answer("pat", 4, 0, [])}
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=prefix&kind=series&prefix=pat&origin=1")
    assert cat.calls[-1] == ("titles", "series", None, "name", 1, 100, "pat", False, None, True, False)
    assert paths(ui)[0] == BASE + "?action=prefix&kind=series&prefix=pat&origin=1&sort=rating&page=1"


def test_prefix_without_filters_keeps_its_old_urls(ui, cat):
    cat.data["prefixes"] = {"ar": answer("ar", 500, 3, [("arm", 497)])}
    run("?action=prefix&kind=series&prefix=ar")
    assert paths(ui)[:2] == [
        BASE + "?action=titles&kind=series&prefix=ar&exact=1&page=1",
        BASE + "?action=prefix&kind=series&prefix=arm",
    ]


def test_other_folder_is_not_offered_under_a_filter(ui, cat):
    # the old digit bucket (letter=0-9) ignores genre/origin on the API side, so it would list unfiltered titles
    cat.data["prefixes"] = {"": answer("", 900, 7, [("a", 400), ("1", 60)])}
    run("?action=prefix&kind=movie&prefix=&digits=1&origin=1")
    assert labels(ui) == ["1 (60)"]
    assert paths(ui) == [BASE + "?action=prefix&kind=movie&prefix=1&origin=1"]
