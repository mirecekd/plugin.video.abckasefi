# tests/test_remote_run.py
"""remote.run(): the main-thread flow (apply on the Kodi thread, dialog closing, timeout, cleanup, error notifications)."""
# ruff: noqa: S105, S106, F401, F811  (fixture tokens are test data; fixtures are imported by name)
import http.client
import socket
from types import SimpleNamespace
from urllib.parse import urlencode

import pytest

from resources.lib import const, remote, remote_page, remote_ui

from .remote_support import (
    FORM,
    HOST,
    env,
    good,
    press,
    settings,
    start_run,
    url_parts,
)


def test_run_applies_the_submission_on_the_main_thread_and_cleans_up(env, settings):
    thread, out, urls = start_run(env)
    port, secret = url_parts(urls[0])
    assert len(secret) == 22 and secret.isascii()
    names = [p.name for p in env.tmp.iterdir()]
    assert names and all(n.startswith("abckasefi_") and secret not in n for n in names)
    conn = http.client.HTTPConnection(HOST, port, timeout=5)
    conn.request("POST", f"/{secret}", urlencode(good(api_token="tok-1")), {"Content-Type": FORM})
    assert conn.getresponse().status == 200
    thread.join(5)
    assert out == [True] and env.notes == [remote_page.text(const.S_RM_SAVED)]
    assert settings.store["catalog_url"] == "https://cat.example.org" and settings.store["api_token"] == "tok-1"
    assert {t.name for t in settings.writers} == {"kodi-main"}  # never a server thread
    assert list(env.tmp.iterdir()) == []
    with pytest.raises(OSError):
        socket.create_connection((HOST, port), timeout=0.5).close()


def test_run_ends_when_the_dialog_is_closed(env, settings):
    thread, out, _urls = start_run(env)
    for code in (7, 100):
        press(env.dialogs[0], code)
    assert not env.dialogs[0].closed
    press(env.dialogs[0], 92)
    thread.join(5)
    assert out == [False] and env.notes == [] and settings.writers == [] and list(env.tmp.iterdir()) == []


@pytest.mark.parametrize("code", [9, 10, 13, 92])
def test_close_actions(env, code):
    dialog = remote_ui.QrDialog("bg.png", "qr.png", "http://h/x")
    press(dialog, code)
    assert dialog.closed


def test_run_times_out(env, settings):
    thread, out, _urls = start_run(env, timeout=0.3)
    thread.join(5)
    assert out == [False] and env.notes == [remote_page.text(const.S_RM_TIMEOUT)]
    assert settings.writers == [] and list(env.tmp.iterdir()) == []


def test_png_names_are_unique_per_run(env, monkeypatch):
    seen = []
    real = remote_ui.temp_file

    def spy(run_id, name, data):
        path = real(run_id, name, data)
        seen.append(path)
        return path

    monkeypatch.setattr(remote_ui, "temp_file", spy)
    for _ in range(2):
        env.dialogs.clear()
        thread, _out, _urls = start_run(env, timeout=0.2)
        thread.join(5)
    assert len(seen) == 4 and len(set(seen)) == 4


def test_no_network_notification(env, monkeypatch):
    monkeypatch.setattr(remote, "lan_ip", lambda: "")
    assert remote.run() is False
    assert env.notes == [remote_page.text(const.S_RM_NO_NETWORK)]


def test_missing_http_server_module_notification(env, monkeypatch):
    def boom(session, host):
        raise ImportError("no http.server")

    monkeypatch.setattr(remote, "start_server", boom)
    assert remote.run(bind_host=HOST) is False
    assert env.notes == [remote_page.text(const.S_RM_NO_SERVER)]


@pytest.mark.parametrize("address,usable", [("192.168.1.20", True), ("10.0.0.5", True), ("127.0.0.1", False),
                                            ("169.254.3.4", False), ("", False), ("0.0.0.0", False)])  # noqa: S104
def test_usable_ip(address, usable):
    assert remote.usable_ip(address) is usable


def test_lan_ip_falls_back_to_kodi_and_rejects_loopback(monkeypatch):
    class BrokenSocket:
        def __init__(self, *args):
            raise OSError("no route")

    monkeypatch.setattr(remote.socket, "socket", BrokenSocket)
    monkeypatch.setattr(remote, "xbmc", SimpleNamespace(getIPAddress=lambda: "192.168.7.7"))
    assert remote.lan_ip() == "192.168.7.7"
    monkeypatch.setattr(remote, "xbmc", SimpleNamespace(getIPAddress=lambda: "169.254.1.1"))
    assert remote.lan_ip() == ""
