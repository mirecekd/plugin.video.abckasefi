# tests/test_urls_cfg.py
"""urls (byte-identical Nokturno URLs) and cfg validation."""
import pytest

from resources.lib import cfg, urls


# ---- urls: the watched mark depends on these strings never changing ----------------------------------------
def test_movie_url_is_the_exact_nokturno_player_url():
    assert urls.nokturno_movie_url("tt0068646") == "plugin://plugin.video.nokturno/?action=play&type=movie&id=tt0068646&ask=1"


def test_episode_url_matches_nokturno_tmdb_helper_player_shape():
    # same shape as resources/players/nokturno.json of Nokturno: id={imdb}%3A{season}%3A{episode}&series={imdb}
    assert urls.nokturno_episode_url("tt0903747", 1, 2) == (
        "plugin://plugin.video.nokturno/?action=play&type=series&id=tt0903747%3A1%3A2&series=tt0903747&ask=1")


def test_series_url_and_episode_ints_are_normalised():
    assert urls.nokturno_series_url("tt0903747") == "plugin://plugin.video.nokturno/?action=seasons&id=tt0903747"
    assert urls.nokturno_episode_url("tt0903747", "01", "02") == urls.nokturno_episode_url("tt0903747", 1, 2)


@pytest.mark.parametrize("bad", ["", "0068646", "tt", "tt12a", "tt1/../../x", "tt1&ask=0", None, 5, "tt12345678901"])
def test_ids_that_are_not_imdb_ids_are_refused_everywhere(bad):
    for build in (urls.nokturno_movie_url, urls.nokturno_series_url, lambda x: urls.nokturno_episode_url(x, 1, 1)):
        with pytest.raises(ValueError):
            build(bad)


def test_build_url_keeps_order_skips_none_and_parses_back():
    url = urls.build_url(action="titles", kind="movie", letter="K", page=2, sort=None)
    assert url == "plugin://plugin.video.abckasefi/?action=titles&kind=movie&letter=K&page=2"
    assert urls.parse_query(url.split("?", 1)[1]) == {"action": "titles", "kind": "movie", "letter": "K", "page": "2"}
    assert urls.build_url() == "plugin://plugin.video.abckasefi/"
    assert urls.parse_query("?q=a%20b&x=") == {"q": "a b", "x": ""}


# ---- cfg ---------------------------------------------------------------------------------------------------
@pytest.mark.parametrize("url", ["http://192.168.1.5:8090", "https://catalog.example.org", "http://nas.local:8090/",
                                 "https://h.example.org:8443"])
def test_http_and_https_catalog_urls_are_accepted(url):
    assert cfg.validate_url(url)[0] is True


@pytest.mark.parametrize("url", ["", "ftp://h/", "file:///etc/passwd", "javascript:alert(1)", "http://", "//host",
                                 "http://user:pw@host", "http://host/?x=1", "http://host/#f", "http://" + "a" * 600,
                                 "http://host:99999999", "host:8090"])
def test_bad_catalog_urls_are_rejected(url):
    assert cfg.validate_url(url)[0] is False


def test_trailing_slash_and_blanks_are_normalised():
    assert cfg.normalize_url("  http://h:8090/// ") == "http://h:8090"


def test_token_rules():
    assert cfg.validate_token("") == (True, "")
    assert cfg.validate_token("  abc_DEF-123  ") == (True, "abc_DEF-123")
    for bad in ("has space", "tab\there", "x" * 257, "dia\u010dkritika", "new\nline"):
        assert cfg.validate_token(bad)[0] is False, bad


@pytest.mark.parametrize("raw,expected", [
    ("100", 100), ("9999", 200), ("1", 20), ("57", 60), ("abc", 100), (None, 100), ("45.0", 50), ("55", 60),
    ("25", 30), ("24", 20), ("195", 200), ("-5", 20)])
def test_items_per_page_is_clamped_and_stepped(raw, expected):
    assert cfg.clamp_per_page(raw) == expected


def test_settings_accessors_use_the_addon_settings(monkeypatch):
    store = {"catalog_url": "http://h:8090/", "api_token": " tok ", "items_per_page": "250", "lang": "2"}
    monkeypatch.setattr(cfg, "get", lambda key, default="": store.get(key, default))
    assert (cfg.base_url(), cfg.token(), cfg.per_page(), cfg.lang(), cfg.configured()) == (
        "http://h:8090", "tok", 200, "en", True)
    store["lang"] = "x"
    assert cfg.lang() == "cs"
