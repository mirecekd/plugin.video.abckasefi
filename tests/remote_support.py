# tests/remote_support.py
"""Shared helpers and fixtures for the phone-setup tests (test_remote*.py import the fixtures from here)."""
# ruff: noqa: S104, S105, S106  (fixture tokens and addresses are test data)
import http.client
import threading
import time
from types import SimpleNamespace
from typing import Any
from urllib.parse import urlencode

import pytest

from resources.lib import cfg, remote, remote_http, remote_ui, texts

HOST = "127.0.0.1"
FORM = "application/x-www-form-urlencoded"
SECRET = "S3cretSecretSecretAA"


class FakeAddon:
    """Stands in for xbmcaddon.Addon: a settings dict plus a record of the thread of every setSetting call."""

    store = {}
    writers = []

    def getSetting(self, key):
        return self.store.get(key, "")

    def setSetting(self, key, value):
        self.writers.append(threading.current_thread())
        self.store[key] = value

    def getLocalizedString(self, string_id):
        return ""  # forces the English fallback texts


@pytest.fixture(autouse=True)
def settings(monkeypatch):
    FakeAddon.store = {"catalog_url": "http://nas.lan:8090", "api_token": "STORED-TOKEN-123", "items_per_page": "100",
                       "lang": "1"}
    FakeAddon.writers = []
    monkeypatch.setattr(cfg, "xbmcaddon", SimpleNamespace(Addon=FakeAddon))
    monkeypatch.setattr(texts, "xbmcaddon", SimpleNamespace(Addon=FakeAddon))
    return FakeAddon


@pytest.fixture
def server():
    session = remote_http.Session(SECRET, HOST, remote.settings_snapshot(), bool(cfg.token()))
    srv = remote_http.start_server(session, HOST)
    yield session
    remote_http.stop_server(srv)


def request(session, method, path=None, body=None, headers=None):
    """One request against the test server; returns (status, body text, response)."""
    conn = http.client.HTTPConnection(HOST, session.port, timeout=5)
    try:
        conn.request(method, path if path is not None else f"/{session.secret}", body=body, headers=headers or {})
        resp = conn.getresponse()
        return resp.status, resp.read().decode("utf-8"), resp
    finally:
        conn.close()


def post(session, fields, headers=None):
    return request(session, "POST", body=urlencode(fields), headers={"Content-Type": FORM, **(headers or {})})


def good(**over):
    fields = {"catalog_url": "https://cat.example.org/", "api_token": "", "items_per_page": "50", "lang": "en"}
    fields.update(over)
    return fields


def press(dialog, code):
    """Deliver a Kodi action with the given id to the dialog."""
    action: Any = SimpleNamespace(getId=lambda: code)
    dialog.onAction(action)


class FakeMonitor:
    def waitForAbort(self, timeout=-1):
        time.sleep(0.02)
        return False


@pytest.fixture
def env(monkeypatch, tmp_path):
    """Fake Kodi around remote.run(): notifications, dialogs created, temp dir for special://temp/."""
    notes = []
    dialogs = []
    monkeypatch.setattr(remote, "xbmc", SimpleNamespace(Monitor=FakeMonitor, getIPAddress=lambda: ""))
    monkeypatch.setattr(remote, "notify", notes.append)
    monkeypatch.setattr(remote_ui, "xbmcvfs", SimpleNamespace(
        translatePath=lambda p: str(tmp_path / p.replace("special://temp/", ""))))

    class Dialog(remote_ui.QrDialog):
        def __init__(self, *args):
            super().__init__(*args)
            dialogs.append(self)

    monkeypatch.setattr(remote_ui, "QrDialog", Dialog)
    return SimpleNamespace(notes=notes, dialogs=dialogs, tmp=tmp_path)


def start_run(env, **kwargs):
    """Run remote.run in a thread named 'kodi-main'; returns (thread, result list, URLs given to make_png)."""
    urls = []
    out = []

    def make_png(url):
        urls.append(url)
        return b"\x89PNG-fake"

    thread = threading.Thread(target=lambda: out.append(remote.run(bind_host=HOST, make_png=make_png, **kwargs)),
                              name="kodi-main")
    thread.start()
    deadline = time.monotonic() + 5
    while not env.dialogs and time.monotonic() < deadline:
        time.sleep(0.01)
    assert env.dialogs, "dialog never shown"
    return thread, out, urls


def url_parts(url):
    hostport, secret = url[len("http://"):].split("/")
    return int(hostport.split(":")[1]), secret
