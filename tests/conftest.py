# tests/conftest.py
"""Shared fixtures. `ui` records the Kodi calls the listing screens make (xbmcplugin functions and xbmcgui.Dialog)."""
import types

import pytest
import xbmcaddon
import xbmcgui
import xbmcplugin

from resources.lib import api, watched
from tests.listing_support import FakeCatalog


class FakeTag:
    """Records every setter call as tag.calls[name] = args, so tests can see e.g. setPlaycount."""

    def __init__(self):
        self.calls = {}

    def __getattr__(self, name):
        def record(*args):
            self.calls[name] = args

        return record


class FakeListItem:
    """Kodistubs' ListItem keeps nothing; this one remembers label, properties and tag calls."""

    def __init__(self, label="", label2="", path="", offscreen=False):
        self.label = label
        self.props = {}
        self.tag = FakeTag()

    def getLabel(self):
        return self.label

    def setProperty(self, key, value):
        self.props[key] = value

    def getProperty(self, key):
        return self.props.get(key, "")

    def getVideoInfoTag(self):
        return self.tag

    def setArt(self, art):
        self.art = art


@pytest.fixture
def cat(monkeypatch):
    """Fake api.Catalog (set results in cat.data[method], read cat.calls) and an empty watched state."""
    FakeCatalog.data = {}
    FakeCatalog.calls = []
    monkeypatch.setattr(api, "Catalog", FakeCatalog)
    monkeypatch.setattr(watched, "load", lambda path=None: {})
    return FakeCatalog


@pytest.fixture
def ui(monkeypatch):
    """Recorder: ui.added (addDirectoryItems batches), ui.ended, ui.content, ui.sorts, ui.dialogs, ui.entries()."""
    rec = types.SimpleNamespace(
        added=[], ended=[], content=[], sorts=[], dialogs=[], settings_opened=0, input_answer="", yesno_answer=False)

    class FakeDialog:
        def notification(self, heading, message, icon="", time=0, sound=True):
            rec.dialogs.append(("notification", message, icon))

        def ok(self, heading, message):
            rec.dialogs.append(("ok", message))
            return True

        def yesno(self, heading, message, *args, **kwargs):
            rec.dialogs.append(("yesno", message))
            return rec.yesno_answer

        def input(self, heading, *args, **kwargs):
            rec.dialogs.append(("input", heading))
            return rec.input_answer

    class FakeAddon:
        def getSetting(self, key):
            return ""

        def getLocalizedString(self, string_id):
            return ""  # forces texts.FALLBACK, so assertions can use the English text

        def openSettings(self):
            rec.settings_opened += 1

    def add(handle, items, totalItems=0):
        rec.added.append(list(items))
        return True

    def end(handle, succeeded=True, updateListing=False, cacheToDisc=True):
        rec.ended.append({"handle": handle, "succeeded": succeeded, "update": updateListing, "cache": cacheToDisc})

    monkeypatch.setattr(xbmcplugin, "addDirectoryItems", add)
    monkeypatch.setattr(xbmcplugin, "endOfDirectory", end)
    monkeypatch.setattr(xbmcplugin, "setContent", lambda handle, content: rec.content.append(content))
    monkeypatch.setattr(xbmcplugin, "addSortMethod", lambda handle, method, *a, **k: rec.sorts.append(method))
    monkeypatch.setattr(xbmcgui, "Dialog", FakeDialog)
    monkeypatch.setattr(xbmcgui, "ListItem", FakeListItem)
    monkeypatch.setattr(xbmcaddon, "Addon", FakeAddon)
    rec.entries = lambda: [entry for batch in rec.added for entry in batch]
    return rec
