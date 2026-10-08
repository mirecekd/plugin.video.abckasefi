# tests/test_listing_router.py
"""Router: error mapping per ApiError kind, parameter checks, unknown action, plain actions."""
import pytest

from resources.lib import api
from tests.listing_support import run

END_FAILED = {"handle": 7, "succeeded": False, "update": False, "cache": True}


@pytest.mark.parametrize("kind,text,dialog", [
    (api.NETWORK, "Cannot reach the catalog. Check the address and the network.", "notification"),
    (api.AUTH, "The catalog refused the token. Check the API token in the settings.", "notification"),
    (api.BUILDING, "The catalog is still being built. Try again in a few minutes.", "notification"),
    (api.SERVER, "The catalog returned an error.", "notification"),
    (api.CERT, "Cannot verify the server's HTTPS certificate.", "ok"),
    (api.NOT_CONFIGURED, "Set the catalog address in the add-on settings first.", "yesno"),
    (api.BAD_URL, "The catalog address must start with http:// or https://.", "yesno"),
])
def test_api_error_kinds_map_to_message_and_fail_the_directory(ui, cat, kind, text, dialog):
    cat.data["letters"] = api.ApiError(kind)
    run("?action=letters&kind=movie")
    shown = [d for d in ui.dialogs if d[0] == dialog]
    assert len(shown) == 1 and shown[0][1].startswith(text)
    assert [d[0] for d in ui.dialogs] == [dialog]
    assert ui.ended == [END_FAILED]
    assert ui.added == []


def test_network_error_notification_uses_error_icon(ui, cat):
    cat.data["letters"] = api.ApiError(api.NETWORK)
    run("?action=letters&kind=movie")
    assert ui.dialogs[0][2] == "error"


def test_not_configured_offers_settings_only_when_accepted(ui, cat):
    cat.data["letters"] = api.ApiError(api.NOT_CONFIGURED)
    run("?action=letters&kind=movie")
    assert ui.settings_opened == 0
    ui.yesno_answer = True
    run("?action=letters&kind=movie")
    assert ui.settings_opened == 1


def test_unexpected_error_never_raises_and_ends_unsuccessfully(ui, cat):
    cat.data["letters"] = RuntimeError("boom token=SECRET")
    run("?action=letters&kind=movie")
    assert ui.ended[-1]["succeeded"] is False
    assert [d[0] for d in ui.dialogs] == ["notification"]
    assert "boom" not in ui.dialogs[0][1]


def test_bad_parameters_do_not_reach_the_catalog(ui, cat):
    run("?action=titles&kind=movie&letter=../x")
    run("?action=titles&kind=bogus&letter=A")
    assert cat.calls == [] and [e["succeeded"] for e in ui.ended] == [False, False]


def test_unknown_action_falls_back_to_root(ui, cat):
    run("?action=nope")
    assert len(ui.entries()) == 5 and ui.ended[-1]["succeeded"] is True


def test_settings_action_opens_settings_and_releases_the_handle(ui, cat):
    run("?action=settings")
    assert ui.settings_opened == 1 and ui.ended[-1]["succeeded"] is False


def test_test_connection_reports_version(ui, cat):
    cat.data["ping"] = {"ok": True, "version": "1.2"}
    run("?action=test_connection")
    assert ("notification", "Catalog OK (version 1.2)", "info") in ui.dialogs


def test_test_connection_error_is_mapped(ui, cat):
    cat.data["ping"] = api.ApiError(api.AUTH)
    run("?action=test_connection")
    assert any(d[0] == "notification" and "refused the token" in d[1] for d in ui.dialogs)


def test_remote_setup_imports_lazily_and_runs(ui, cat, monkeypatch):
    from resources.lib import remote

    called = []
    monkeypatch.setattr(remote, "run", lambda *a, **k: called.append(1))
    run("?action=remote_setup")
    assert called == [1]


def test_argv_is_reread_on_every_run(ui, cat):
    run("?action=kind&kind=movie", handle=3)
    run("?action=kind&kind=series", handle=4)
    assert [e["handle"] for e in ui.ended] == [3, 4]
    assert ui.entries()[0][0].endswith("kind=movie") and ui.entries()[3][0].endswith("kind=series")
