# tests/test_resume.py
"""Resume screen (action=resume): continue, next episode and all seasons, built from a temporary MyVideos database."""

import pytest

from resources.lib import api, listing_resume, recent, totals, urls
from resources.lib.const import NOKTURNO_BASE
from tests.listing_support import BASE, labels, run
from tests.recent_support import EP, EP_OTHER, make_db

TT = "tt0000009"
ALL_SEASONS = (BASE + "?action=seasons&id=" + TT, "All seasons", True)


@pytest.fixture
def screen(tmp_path, monkeypatch, ui, cat):
    """screen(rows, bookmarks=(), counts={1: 10, 2: 10}): prepare the database and the cached season sizes."""
    saved = {}

    def prepare(rows, bookmarks=(), counts=None):
        path = make_db(tmp_path, rows, bookmarks)
        monkeypatch.setattr(recent.watched, "db_path", lambda: path)
        monkeypatch.setattr(totals, "load", lambda path=None: {TT: counts} if counts else {})
        monkeypatch.setattr(totals, "save", lambda tt, data, path=None: saved.update({tt: data}))
        return saved

    return prepare


def shown(ui):
    return [(path, item.getLabel(), folder) for path, item, folder in ui.entries()]


def playable(ui):
    return [item.getProperty("IsPlayable") for _path, item, _folder in ui.entries()]


def test_half_watched_episode_gives_continue_then_next_then_all_seasons(ui, screen):
    ep = EP.format(2, 5)
    screen([(ep, "2026-03-01 10:00:00", NOKTURNO_BASE, 0)], {ep: (1380.0, 2700.0)}, {1: 10, 2: 10})
    run("?action=resume&id=" + TT)
    assert shown(ui) == [
        (urls.nokturno_episode_url(TT, 2, 5), "Continue: S02E05 (in progress, 23 min)", False),
        (urls.nokturno_episode_url(TT, 2, 6), "Next episode: S02E06", False),
        ALL_SEASONS,
    ]
    assert playable(ui) == ["true", "true", ""]
    assert ui.ended[-1]["succeeded"] is True


def test_finished_episode_has_no_continue_item(ui, screen):
    screen([(EP.format(2, 5), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)], counts={1: 10, 2: 10})
    run("?action=resume&id=" + TT)
    assert labels(ui) == ["Next episode: S02E06", "All seasons"]


def test_last_episode_of_a_season_moves_to_the_next_season(ui, screen):
    screen([(EP.format(1, 10), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)], counts={1: 10, 2: 8})
    run("?action=resume&id=" + TT)
    assert shown(ui)[0][:2] == (urls.nokturno_episode_url(TT, 2, 1), "Next episode: S02E01")


def test_end_of_the_series_has_no_next_item(ui, screen):
    screen([(EP.format(2, 10), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)], counts={1: 10, 2: 10})
    run("?action=resume&id=" + TT)
    assert shown(ui) == [ALL_SEASONS]


def test_specials_are_skipped_when_moving_on_but_not_from_them(ui, screen):
    screen([(EP.format(1, 4), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)], counts={0: 5, 1: 4, 2: 3})
    run("?action=resume&id=" + TT)
    assert labels(ui)[0] == "Next episode: S02E01"
    assert listing_resume.next_episode({0: 5, 1: 4}, 1, 4) is None  # the specials are never "the next season"
    assert listing_resume.next_episode({0: 5, 1: 4}, 0, 5) == (1, 1)  # watching a special leads into season 1
    assert listing_resume.next_episode({0: 5, 1: 4}, 0, 2) == (0, 3)


def test_anchor_is_the_last_played_not_the_highest_episode(ui, screen):
    screen(
        [
            (EP.format(2, 9), "2026-01-01 10:00:00", NOKTURNO_BASE, 1),
            (EP.format(1, 3), "2026-03-01 10:00:00", NOKTURNO_BASE, 1),
        ],
        counts={1: 10, 2: 10},
    )
    run("?action=resume&id=" + TT)
    assert labels(ui) == ["Next episode: S01E04", "All seasons"]


def test_other_shows_do_not_leak_into_the_screen(ui, screen):
    screen(
        [
            (EP.format(1, 1), "2026-01-01 10:00:00", NOKTURNO_BASE, 1),
            (EP_OTHER.format(5, 5), "2026-06-01 10:00:00", NOKTURNO_BASE, 1),
        ],
        counts={1: 10},
    )
    run("?action=resume&id=" + TT)
    assert labels(ui) == ["Next episode: S01E02", "All seasons"]


@pytest.mark.parametrize(
    "seconds,text", [(5, "<1 min"), (59, "<1 min"), (60, "1 min"), (61, "2 min"), (1380, "23 min")]
)
def test_minutes_are_rounded_up_and_short_times_say_less_than_a_minute(ui, screen, seconds, text):
    ep = EP.format(1, 1)
    screen([(ep, "", NOKTURNO_BASE, 0)], {ep: (float(seconds), 3000.0)}, {1: 3})
    run("?action=resume&id=" + TT)
    assert labels(ui)[0] == f"Continue: S01E01 (in progress, {text})"


def test_season_sizes_come_from_the_catalog_and_are_cached(ui, cat, screen):
    saved = screen([(EP.format(1, 2), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)])
    cat.data["seasons"] = {"seasons": [{"season": 1, "episodes": 2}, {"season": 2, "episodes": 6}]}
    run("?action=resume&id=" + TT)
    assert labels(ui) == ["Next episode: S02E01", "All seasons"]
    assert saved == {TT: {1: 2, 2: 6}}
    assert ("seasons", TT) in cat.calls


def test_cached_sizes_spare_the_catalog(ui, cat, screen):
    screen([(EP.format(1, 2), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)], counts={1: 5})
    run("?action=resume&id=" + TT)
    assert not [call for call in cat.calls if call[0] == "seasons"]


def test_catalog_error_keeps_continue_and_all_seasons(ui, cat, screen):
    ep = EP.format(1, 2)
    screen([(ep, "2026-03-01 10:00:00", NOKTURNO_BASE, 0)], {ep: (600.0, 2400.0)})
    cat.data["seasons"] = api.ApiError(api.SERVER, "500")
    run("?action=resume&id=" + TT)
    assert labels(ui) == ["Continue: S01E02 (in progress, 10 min)", "All seasons"]
    assert ui.ended[-1]["succeeded"] is True


@pytest.mark.parametrize("kind", [api.NOT_CONFIGURED, api.BAD_URL, api.AUTH, api.CERT])
def test_setup_errors_reach_the_router(ui, cat, screen, kind):
    screen([(EP.format(1, 2), "2026-03-01 10:00:00", NOKTURNO_BASE, 1)])
    cat.data["seasons"] = api.ApiError(kind)
    run("?action=resume&id=" + TT)
    assert ui.entries() == [] and ui.ended[-1]["succeeded"] is False
    assert [d for d in ui.dialogs if d[0] in ("notification", "ok", "yesno")]


def test_missing_database_shows_only_all_seasons(ui, cat, tmp_path, monkeypatch):
    monkeypatch.setattr(recent.watched, "db_path", lambda: str(tmp_path / "missing.db"))
    run("?action=resume&id=" + TT)
    assert shown(ui) == [ALL_SEASONS]
    assert not [call for call in cat.calls if call[0] == "seasons"]


def test_bad_id_is_refused(ui, cat):
    run("?action=resume&id=oops")
    assert ui.entries() == [] and ui.ended[-1]["succeeded"] is False


def test_unknown_size_of_the_current_season_does_not_skip_its_rest():
    # regression: with no cached size for season 1 the next episode jumped straight to season 2
    assert listing_resume.next_episode({2: 8}, 1, 3) == (1, 4)
    assert listing_resume.next_episode({1: 10, 2: 8}, 1, 10) == (2, 1)
    assert listing_resume.next_episode({1: 10, 2: 8}, 2, 8) is None
