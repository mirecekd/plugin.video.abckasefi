# resources/lib/texts.py
"""Localized strings: Kodi's getLocalizedString with an English fallback so a missing .po entry never shows a number."""

from . import const

try:
    import xbmcaddon
except ImportError:  # unit tests without Kodi stubs
    xbmcaddon = None

FALLBACK = {
    const.S_ADDON_NAME: "ABCKASEFI",
    const.S_MOVIES: "Movies",
    const.S_SERIES: "Series",
    const.S_SEARCH: "Search",
    const.S_TMDB_LISTS: "TMDB lists",
    const.S_NEXT_PAGE: "Next page",
    const.S_SETTINGS: "Settings",
    const.S_ERR_NOT_CONFIGURED: "Set the catalog address in the add-on settings first.",
    const.S_ERR_NETWORK: "Cannot reach the catalog. Check the address and the network.",
    const.S_ERR_AUTH: "The catalog refused the token. Check the API token in the settings.",
    const.S_ERR_CERT: (
        "Cannot verify the server's HTTPS certificate. Check the date and time on the device, "
        "update script.module.certifi, or use a different catalog URL. The connection was not made."
    ),
    const.S_ERR_BUILDING: "The catalog is still being built. Try again in a few minutes.",
    const.S_ERR_SERVER: "The catalog returned an error.",
    const.S_NO_RESULTS: "Nothing found.",
    const.S_SEASON_N: "Season {}",
    const.S_SPECIALS: "Specials",
    const.S_NO_EPISODES: "No episode data for this series.",
    const.S_TEST_OK: "Catalog OK (version {})",
    const.S_ERR_NO_NOKTURNO: "The Nokturno add-on is not installed.",
    const.S_ERR_BAD_URL: "The catalog address must start with http:// or https://.",
    const.S_SORT_NAME: "By name",
    const.S_SORT_RATING: "By rating",
    const.S_SORT_YEAR: "By year",
    const.S_ERR_BAD_INPUT: "Invalid input.",
    const.S_WATCHED_EPS: "{}/{} watched",
    const.S_RECENT: "Recently watched",
    const.S_INFO: "Information",
    const.S_SORT_VOTES: "By votes",
    const.S_SORT_TMDB: "TMDB order",
    const.S_EXACT_FOLDER: "{} (exact, {})",
    const.S_OTHER_FOLDER: "Other ({})",
    const.S_RESUME_CONTINUE: "Continue: {} (in progress, {})",
    const.S_RESUME_NEXT: "Next episode: {}",
    const.S_ALL_SEASONS: "All seasons",
    const.S_LESS_THAN_MINUTE: "<1 min",
    const.S_MINUTES: "{} min",
}


def t(string_id):
    """Text for a string id; falls back to the English default (or the id) when Kodi has no translation."""
    if xbmcaddon is not None:
        text = xbmcaddon.Addon().getLocalizedString(string_id)
        if text:
            return text
    return FALLBACK.get(string_id, str(string_id))


def tf(string_id, *args):
    """Localized text with {} placeholders filled."""
    return t(string_id).format(*args)
