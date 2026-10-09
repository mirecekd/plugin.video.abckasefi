# tests/test_listing_prefix.py
"""Prefix drill-down (action=prefix): folders with counts, descent, title listing, exact folder, depth limit, errors."""

from tests.listing_support import BASE, labels, movie, run


def answer(prefix, total, exact, children):
    return {"prefix": prefix, "total": total, "exact": exact, "children": [{"prefix": p, "n": n} for p, n in children]}


def paths(ui):
    return [path for path, _item, _folder in ui.entries()]


def test_letter_a_shows_child_folders_with_counts(ui, cat):
    cat.data["prefixes"] = {"a": answer("a", 500, 0, [("ar", 384), ("as", 116)])}
    run("?action=prefix&kind=movie&prefix=a")
    assert labels(ui) == ["AR (384)", "AS (116)"]
    assert paths(ui) == [BASE + "?action=prefix&kind=movie&prefix=ar", BASE + "?action=prefix&kind=movie&prefix=as"]
    assert cat.calls == [("prefixes", "movie", "a")]
    assert ui.content == ["files"]


def test_descent_a_ar_arm_then_titles(ui, cat):
    cat.data["prefixes"] = {
        "a": answer("a", 500, 0, [("ar", 384), ("as", 116)]),
        "ar": answer("ar", 384, 0, [("arm", 200), ("art", 184)]),
        "arm": answer("arm", 90, 2, [("arma", 90)]),
    }
    cat.data["titles"] = {"has_more": False, "items": [movie(1), movie(2)]}
    run("?action=prefix&kind=movie&prefix=ar")
    assert labels(ui) == ["ARM (200)", "ART (184)"]
    assert paths(ui)[0] == BASE + "?action=prefix&kind=movie&prefix=arm"
    ui.added.clear()
    run("?action=prefix&kind=movie&prefix=arm")
    assert cat.calls[-1] == ("titles", "movie", None, "name", 1, 100, "arm", False)
    assert labels(ui)[1:] == ["Movie 1 (2000)", "Movie 2 (2000)"]


def test_titles_listed_when_total_fits_the_page_size(ui, cat):
    cat.data["prefixes"] = {"ar": answer("ar", 100, 0, [("arm", 60), ("art", 40)])}
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=prefix&kind=movie&prefix=ar")
    assert [c[0] for c in cat.calls] == ["prefixes", "titles"]
    assert paths(ui)[0] == BASE + "?action=prefix&kind=movie&prefix=ar&sort=rating&page=1"
    assert ui.content == ["movies"]


def test_total_above_page_size_shows_folders_not_titles(ui, cat):
    cat.data["prefixes"] = {"ar": answer("ar", 101, 0, [("arm", 60), ("art", 41)])}
    run("?action=prefix&kind=movie&prefix=ar")
    assert [c[0] for c in cat.calls] == ["prefixes"]
    assert labels(ui) == ["ARM (60)", "ART (41)"]


def test_no_children_lists_titles_even_above_the_page_size(ui, cat):
    cat.data["prefixes"] = {"zz": answer("zz", 900, 900, [])}
    cat.data["titles"] = {"has_more": True, "items": [movie(1)]}
    run("?action=prefix&kind=movie&prefix=zz")
    assert cat.calls[-1][0] == "titles"
    assert paths(ui)[-1] == BASE + "?action=prefix&kind=movie&prefix=zz&sort=name&page=2"


def test_depth_limit_of_eight_lists_titles(ui, cat):
    cat.data["prefixes"] = {
        "abcdefg": answer("abcdefg", 900, 0, [("abcdefga", 450), ("abcdefgb", 450)]),
        "abcdefga": answer("abcdefga", 450, 0, [("abcdefgaa", 200), ("abcdefgab", 250)]),
    }
    run("?action=prefix&kind=movie&prefix=abcdefg")
    assert labels(ui) == ["ABCDEFGA (450)", "ABCDEFGB (450)"]
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    ui.added.clear()
    run("?action=prefix&kind=movie&prefix=abcdefga")
    assert cat.calls[-1][0] == "titles" and cat.calls[-1][6] == "abcdefga"


def test_exact_folder_comes_first_and_opens_exact_titles(ui, cat):
    cat.data["prefixes"] = {"ar": answer("ar", 500, 3, [("arm", 300), ("art", 197)])}
    cat.data["titles"] = {"has_more": False, "items": [movie(1)]}
    run("?action=prefix&kind=series&prefix=ar")
    assert labels(ui) == ["AR (exact, 3)", "ARM (300)", "ART (197)"]
    assert paths(ui)[0] == BASE + "?action=titles&kind=series&prefix=ar&exact=1&page=1"
    ui.added.clear()
    run("?action=titles&kind=series&prefix=ar&exact=1&page=1")
    assert cat.calls[-1] == ("titles", "series", None, "name", 1, 100, "ar", True)
    assert paths(ui)[0] == BASE + "?action=titles&kind=series&prefix=ar&exact=1&sort=rating&page=1"


def test_single_child_without_exact_is_skipped(ui, cat):
    cat.data["prefixes"] = {
        "q": answer("q", 500, 0, [("qu", 500)]),
        "qu": answer("qu", 500, 0, [("qua", 300), ("que", 200)]),
    }
    run("?action=prefix&kind=movie&prefix=q")
    assert labels(ui) == ["QUA (300)", "QUE (200)"]
    assert [c[2] for c in cat.calls] == ["q", "qu"]


def test_single_child_with_exact_is_not_skipped(ui, cat):
    cat.data["prefixes"] = {"q": answer("q", 500, 4, [("qu", 496)])}
    run("?action=prefix&kind=movie&prefix=q")
    assert labels(ui) == ["Q (exact, 4)", "QU (496)"]


def test_paging_keeps_sort_in_next_page(ui, cat):
    cat.data["prefixes"] = {"ar": answer("ar", 90, 0, [("arm", 50), ("art", 40)])}
    cat.data["titles"] = {"has_more": True, "items": [movie(1)]}
    run("?action=prefix&kind=movie&prefix=ar&sort=votes&page=2")
    assert cat.calls[-1][3:5] == ("votes", 2)
    assert paths(ui)[-1] == BASE + "?action=prefix&kind=movie&prefix=ar&sort=votes&page=3"
    assert ui.ended[-1]["update"] is True
    assert len(ui.entries()) == 2  # no sort switch on page two


def test_page_one_has_sort_switch_that_cycles(ui, cat):
    cat.data["prefixes"] = {"ar": answer("ar", 5, 0, [])}
    cat.data["titles"] = {"has_more": False, "items": []}
    run("?action=prefix&kind=movie&prefix=ar&sort=rating")
    assert labels(ui)[0] == "By rating -> By votes"
    assert paths(ui)[0] == BASE + "?action=prefix&kind=movie&prefix=ar&sort=votes&page=1"
    assert ("notification", "Nothing found.", "info") in ui.dialogs


def test_digits_screen_shows_only_digit_children_and_other(ui, cat):
    cat.data["prefixes"] = {
        "": answer("", 900, 7, [("a", 400), ("b", 300), ("1", 60), ("2", 40), ("9", 93)]),
    }
    run("?action=prefix&kind=movie&prefix=&digits=1")
    assert labels(ui) == ["Other (7)", "1 (60)", "2 (40)", "9 (93)"]
    assert paths(ui)[0] == BASE + "?action=titles&kind=movie&letter=0-9&page=1"
    assert paths(ui)[1] == BASE + "?action=prefix&kind=movie&prefix=1"
    assert cat.calls == [("prefixes", "movie", "")]


def test_digits_screen_with_a_single_digit_descends(ui, cat):
    cat.data["prefixes"] = {
        "": answer("", 900, 0, [("a", 800), ("1", 100)]),
        "1": answer("1", 300, 0, [("12", 160), ("19", 140)]),
    }
    run("?action=prefix&kind=movie&prefix=&digits=1")
    assert labels(ui) == ["12 (160)", "19 (140)"]
