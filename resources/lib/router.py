# resources/lib/router.py
"""Entry dispatcher: parses the plugin argv, runs one action and turns every failure into a message, never a traceback."""
import sys

import xbmcaddon
import xbmcgui
import xbmcplugin

from . import (
    api,
    detail,
    listing,
    listing_common,
    listing_recent,
    listing_series,
    texts,
    urls,
)
from .const import (
    S_ADDON_NAME,
    S_ERR_AUTH,
    S_ERR_BAD_INPUT,
    S_ERR_BAD_URL,
    S_ERR_BUILDING,
    S_ERR_CERT,
    S_ERR_NETWORK,
    S_ERR_NOT_CONFIGURED,
    S_ERR_SERVER,
    S_TEST_OK,
)
from .log import log

ERROR_TEXTS = {
    api.NOT_CONFIGURED: S_ERR_NOT_CONFIGURED,
    api.BAD_URL: S_ERR_BAD_URL,
    api.NETWORK: S_ERR_NETWORK,
    api.AUTH: S_ERR_AUTH,
    api.CERT: S_ERR_CERT,
    api.BUILDING: S_ERR_BUILDING,
    api.SERVER: S_ERR_SERVER,
}
NEEDS_SETTINGS = (api.NOT_CONFIGURED, api.BAD_URL)


def open_settings(handle=None, params=None):
    xbmcaddon.Addon().openSettings()


def test_connection(handle=None, params=None):
    info = api.Catalog().ping() or {}
    listing_common.notify(texts.tf(S_TEST_OK, info.get("version", "?")))


def remote_setup(handle=None, params=None):
    # imported lazily so this module loads even where remote.py (and its QR code) is not needed
    from . import remote

    # The settings button closes (and saves) the settings dialog before this runs (<close> in settings.xml), so
    # setSetting writes straight to disk instead of into a dialog that may be cancelled. Reopen it to show the result.
    if remote.run():
        xbmcaddon.Addon().openSettings()


DIRECTORY_ACTIONS = {
    "root": listing.root,
    "kind": listing.kind_menu,
    "letters": listing.letters,
    "titles": listing.titles,
    "search": listing.search,
    "lists": listing.lists,
    "tmdb_list": listing.tmdb_list,
    "seasons": listing_series.seasons,
    "episodes": listing_series.episodes,
    "recent": listing_recent.recently_watched,
}
PLAIN_ACTIONS = {"settings": open_settings, "test_connection": test_connection, "remote_setup": remote_setup,
                 "detail": detail.show}


def show_error(error):
    """Tell the user what went wrong in words; configuration problems offer to open the settings."""
    message = texts.t(ERROR_TEXTS.get(error.kind, S_ERR_SERVER))
    dialog = xbmcgui.Dialog()
    if error.kind in NEEDS_SETTINGS:
        if dialog.yesno(texts.t(S_ADDON_NAME), message):
            xbmcaddon.Addon().openSettings()
    elif error.kind == api.CERT:
        dialog.ok(texts.t(S_ADDON_NAME), message)  # long text: a notification would cut it off
    else:
        dialog.notification(texts.t(S_ADDON_NAME), message, xbmcgui.NOTIFICATION_ERROR)


def run(argv):
    """argv = [base, handle, query, ...] exactly as Kodi passes it; read on every call (the invoker is reused)."""
    handle = int(argv[1]) if len(argv) > 1 and str(argv[1]).lstrip("-").isdigit() else -1
    params = urls.parse_query(argv[2]) if len(argv) > 2 else {}
    action = params.get("action", "root")
    try:
        if action in PLAIN_ACTIONS:
            PLAIN_ACTIONS[action](handle, params)
            if handle >= 0:
                xbmcplugin.endOfDirectory(handle, succeeded=False)  # a folder item was clicked: release Kodi
        else:
            DIRECTORY_ACTIONS.get(action, listing.root)(handle, params)
    except api.ApiError as error:
        log(f"action {action}: api error {error.kind}")
        show_error(error)
        _close_failed(handle)
    except Exception as exc:  # noqa: BLE001 - last line of defence, the user must not see a traceback
        log(f"action {action}: {type(exc).__name__}: {exc}")
        xbmcgui.Dialog().notification(texts.t(S_ADDON_NAME), texts.t(S_ERR_BAD_INPUT), xbmcgui.NOTIFICATION_ERROR)
        _close_failed(handle)


def _close_failed(handle):
    if handle >= 0:
        xbmcplugin.endOfDirectory(handle, succeeded=False)


if __name__ == "__main__":
    run(sys.argv)
