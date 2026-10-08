# tests/test_totals.py
"""totals.py: the on-disk memory of how many episodes each series has."""
import json

from resources.lib import totals


def test_save_then_load_round_trip(tmp_path):
    path = str(tmp_path / "sub" / "t.json")
    totals.save("tt0000001", {1: 8, 2: 10}, path)
    totals.save("tt0000002", {1: 3}, path)
    assert totals.load(path) == {"tt0000001": {1: 8, 2: 10}, "tt0000002": {1: 3}}


def test_save_replaces_the_entry_of_the_same_series(tmp_path):
    path = str(tmp_path / "t.json")
    totals.save("tt0000001", {1: 8}, path)
    totals.save("tt0000001", {1: 8, 2: 9}, path)
    assert totals.load(path) == {"tt0000001": {1: 8, 2: 9}}


def test_missing_or_corrupt_file_is_an_empty_cache_not_an_error(tmp_path):
    assert totals.load(str(tmp_path / "nope.json")) == {}
    bad = tmp_path / "bad.json"
    bad.write_text("{not json")
    assert totals.load(str(bad)) == {}
    bad.write_text(json.dumps(["a", "list"]))
    assert totals.load(str(bad)) == {}
    bad.write_text(json.dumps({"tt1": {"x": "y", "2": "3"}, "tt2": "oops"}))
    assert totals.load(str(bad)) == {"tt1": {2: 3}}


def test_unwritable_location_does_not_raise(tmp_path):
    blocker = tmp_path / "file"
    blocker.write_text("x")
    totals.save("tt0000001", {1: 1}, str(blocker / "t.json"))  # a path below a regular file cannot be created


def test_the_cache_is_capped(tmp_path, monkeypatch):
    monkeypatch.setattr(totals, "MAX_SERIES", 3)
    path = str(tmp_path / "t.json")
    for n in range(1, 6):
        totals.save(f"tt{n:07d}", {1: n}, path)
    assert list(totals.load(path)) == ["tt0000003", "tt0000004", "tt0000005"]


def test_no_xbmcvfs_means_no_cache(monkeypatch):
    monkeypatch.setattr(totals, "xbmcvfs", None)
    assert totals.load() == {}
    totals.save("tt0000001", {1: 1})
