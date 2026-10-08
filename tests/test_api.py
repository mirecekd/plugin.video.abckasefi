# tests/test_api.py
"""The catalog client: how failures are classified, which requests are made, and that nothing but http(s) is opened."""
import io
import ssl
import urllib.error
import urllib.request
from email.message import Message
from http.client import HTTPMessage

import pytest

from resources.lib import api


class _Resp:
    def __init__(self, body):
        self.body = body

    def read(self):
        return self.body

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _raising(exc):
    def fake(request, timeout=None, context=None):
        raise exc
    return fake


def _kind(monkeypatch, exc):
    monkeypatch.setattr(api, "_open", _raising(exc))
    with pytest.raises(api.ApiError) as caught:
        api.fetch("http://h:8090", "t", "/v1/ping")
    return caught.value.kind


def test_http_status_codes_map_to_error_kinds(monkeypatch):
    def err(code):
        return urllib.error.HTTPError("u", code, "m", Message(), None)
    assert _kind(monkeypatch, err(401)) == api.AUTH
    assert _kind(monkeypatch, err(403)) == api.AUTH
    assert _kind(monkeypatch, err(503)) == api.BUILDING
    assert _kind(monkeypatch, err(500)) == api.SERVER
    assert _kind(monkeypatch, err(404)) == api.SERVER


def test_network_and_certificate_failures_are_told_apart(monkeypatch):
    assert _kind(monkeypatch, urllib.error.URLError(ConnectionRefusedError())) == api.NETWORK
    assert _kind(monkeypatch, TimeoutError()) == api.NETWORK
    cert = urllib.error.URLError(ssl.SSLCertVerificationError(1, "certificate verify failed"))
    assert _kind(monkeypatch, cert) == api.CERT


def test_bad_or_empty_base_url_never_reaches_the_network(monkeypatch):
    monkeypatch.setattr(api, "_open", _raising(AssertionError("network must not be touched")))
    for base, kind in (("", api.NOT_CONFIGURED), ("ftp://x", api.BAD_URL), ("file:///etc/passwd", api.BAD_URL)):
        with pytest.raises(api.ApiError) as caught:
            api.fetch(base, "t", "/v1/ping")
        assert caught.value.kind == kind


def test_invalid_json_is_a_server_error(monkeypatch):
    monkeypatch.setattr(api, "_open", lambda *a, **k: _Resp(b"<html>not json"))
    with pytest.raises(api.ApiError) as caught:
        api.fetch("http://h:8090", "", "/v1/ping")
    assert caught.value.kind == api.SERVER


def test_https_uses_a_verifying_context_and_http_uses_none(monkeypatch):
    seen = []

    def fake(request, timeout=None, context=None):
        seen.append((request.full_url, context))
        return _Resp(b'{"ok": true}')

    monkeypatch.setattr(api, "_open", fake)
    assert api.fetch("https://c.example.org", "tok", "/v1/ping") == {"ok": True}
    assert api.fetch("http://192.168.1.5:8090", "", "/v1/ping") == {"ok": True}
    (https_url, https_ctx), (http_url, http_ctx) = seen
    assert https_url == "https://c.example.org/v1/ping?token=tok" and https_ctx.verify_mode == ssl.CERT_REQUIRED
    assert http_url == "http://192.168.1.5:8090/v1/ping" and http_ctx is None


def test_catalog_builds_the_expected_requests(monkeypatch):
    calls = []
    monkeypatch.setattr(api, "fetch", lambda base, token, path, params=None, **kw: calls.append((path, params)) or {})
    cat = api.Catalog("http://h:8090", "tok", "sk")
    cat.titles("movie", "K", "rating", 2, 100)
    cat.tmdb_list("series", "trending_day", 1, 100, "rating")
    cat.episodes("tt0903747", 1)
    assert calls[0] == ("/v1/titles", {"type": "movie", "letter": "K", "sort": "rating", "page": 2,
                                       "per_page": 100, "lang": "sk"})
    assert calls[1] == ("/v1/list/series/trending_day", {"page": 1, "per_page": 100, "sort": "rating", "lang": "sk"})
    assert calls[2] == ("/v1/title/tt0903747/season/1", {"lang": "sk"})
    with pytest.raises(ValueError):
        cat.title("not-an-id")
    assert cat.poster_url("tt0068646") == "http://h:8090/v1/poster/tt0068646?size=w342&token=tok"


def test_the_opener_refuses_everything_but_http_and_https():
    # the real (unpatched) opener: a file:, ftp: or data: URL must raise URLError, never open
    for url in ("file:///etc/passwd", "ftp://example.org/x", "data:text/plain,hi"):
        with pytest.raises(urllib.error.URLError):
            api._open(urllib.request.Request(url), 2, None)


def _redirect(request, code, location):
    """Call the real redirect handler with correctly typed arguments (HTTPMessage headers, a file-like body)."""
    return api._SafeRedirect().redirect_request(request, io.BytesIO(b""), code, "x", HTTPMessage(), location)


# ---- redirects: the token must never be sent in clear because of a redirect ---------------------------------
@pytest.fixture()
def redirecting_server():
    """A real local HTTP server: /same -> 302 to /final (same scheme), /insecure -> 302 to http://other/..., /file -> file:."""
    import http.server
    import threading

    hits = []

    class Handler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            hits.append(self.path)
            if self.path.startswith("/same"):
                self.send_response(302)
                self.send_header("Location", "/final")
            elif self.path.startswith("/insecure"):
                self.send_response(302)
                self.send_header("Location", "http://127.0.0.1:9/leak?token=secret")
            elif self.path.startswith("/file"):
                self.send_response(302)
                self.send_header("Location", "file:///etc/passwd")
            else:
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                self.wfile.write(b'{"final": true}')
                return
            self.end_headers()

        def log_message(self, format, *args):  # noqa: A002 - same signature as the base class, silences stderr
            pass

    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{server.server_address[1]}", hits
    server.shutdown()
    server.server_close()


def test_a_same_scheme_redirect_is_followed(redirecting_server):
    base, hits = redirecting_server
    assert api.fetch(base, "tok", "/same") == {"final": True}
    assert hits[0].startswith("/same?token=tok") and hits[-1] == "/final"


def test_redirect_to_a_file_url_is_refused(redirecting_server):
    base, _hits = redirecting_server
    with pytest.raises(api.ApiError):
        api.fetch(base, "tok", "/file")


def test_https_to_http_redirect_is_refused_before_a_second_request_is_made():
    # regression: the stock redirect handler would follow an https -> http 302 and send the token in clear
    request = urllib.request.Request("https://catalog.example.org/v1/ping?token=secret")
    with pytest.raises(urllib.error.HTTPError):
        _redirect(request, 302, "http://catalog.example.org/v1/ping?token=secret")
    with pytest.raises(urllib.error.HTTPError):
        _redirect(request, 302, "ftp://catalog.example.org/x")
    ok = _redirect(request, 302, "https://catalog.example.org/v1/other")
    assert ok is not None and ok.full_url == "https://catalog.example.org/v1/other"


def test_http_to_https_upgrade_is_allowed():
    request = urllib.request.Request("http://catalog.example.org/v1/ping")
    ok = _redirect(request, 301, "https://catalog.example.org/v1/ping")
    assert ok is not None and ok.full_url.startswith("https://")
