# resources/lib/api.py
"""Client for the abckasefi-catalog HTTP API (stdlib urllib; HTTPS is always certificate-verified)."""

import json
import ssl
import urllib.error
import urllib.request
from urllib.parse import quote, urlencode, urlsplit

from . import cfg, tls
from .const import HTTP_TIMEOUT
from .log import log
from .urls import check_tt

NOT_CONFIGURED, NETWORK, AUTH, CERT, BUILDING, SERVER, BAD_URL = (
    "not_configured",
    "network",
    "auth",
    "cert",
    "building",
    "server",
    "bad_url",
)


class ApiError(Exception):
    """kind is one of the constants above; the UI maps it to a localized message."""

    def __init__(self, kind, detail=""):
        super().__init__(f"{kind}: {detail}")
        self.kind = kind
        self.detail = detail


def _query(params):
    return urlencode([(k, v) for k, v in params.items() if v is not None and v != ""])


class _SafeRedirect(urllib.request.HTTPRedirectHandler):
    """Follow redirects, but never from https to http (the token rides in the query string) and never off http(s)."""

    def redirect_request(self, req, fp, code, msg, headers, newurl):
        target = urlsplit(newurl).scheme
        if target not in ("http", "https") or (req.full_url.startswith("https://") and target != "https"):
            raise urllib.error.HTTPError(req.full_url, code, "redirect to an insecure location refused", headers, fp)
        return super().redirect_request(req, fp, code, msg, headers, newurl)


def _open(request, timeout, context):
    """Open a request with an opener that only knows http and https: file:, ftp: and data: URLs cannot be opened
    through it even by mistake. `context` is a verifying SSLContext for https (None only for plain http)."""
    opener = urllib.request.OpenerDirector()  # build_opener() would add file:/ftp:/data: handlers back
    opener.add_handler(urllib.request.HTTPHandler())
    opener.add_handler(urllib.request.HTTPSHandler(context=context))
    opener.add_handler(urllib.request.HTTPDefaultErrorHandler())
    opener.add_handler(_SafeRedirect())
    opener.add_handler(urllib.request.HTTPErrorProcessor())
    opener.add_handler(urllib.request.UnknownHandler())  # any other scheme (file:, ftp:, data:) -> URLError, never None
    return opener.open(request, timeout=timeout)


def _read(url, timeout, context):
    """One GET. Only http(s) URLs get here: fetch() validates the scheme first (no file:, ftp:, custom schemes)."""
    if not url.startswith(("http://", "https://")):
        raise ApiError(BAD_URL)
    # Only http(s) reaches this line (checked above) and _open() has no handler for any other scheme.
    request = urllib.request.Request(url, headers={"Accept": "application/json", "User-Agent": "abckasefi-kodi/0.1"})
    with _open(request, timeout, context) as response:
        raw = response.read().decode("utf-8")
    try:
        return json.loads(raw)
    except ValueError as exc:
        raise ApiError(SERVER, "invalid JSON") from exc


def fetch(base, token, path, params=None, timeout=HTTP_TIMEOUT):
    """GET base+path with the token appended; returns parsed JSON or raises ApiError."""
    ok, _why = cfg.validate_url(base)
    if not ok:
        raise ApiError(BAD_URL if base else NOT_CONFIGURED)
    query = _query(dict(params or {}, token=token or None))
    url = f"{cfg.normalize_url(base)}{path}" + (f"?{query}" if query else "")
    context = tls.ssl_context() if url.startswith("https://") else None  # None only ever for plain http
    try:
        return _read(url, timeout, context)
    except urllib.error.HTTPError as exc:
        log(f"HTTP {exc.code} for {path}")
        if exc.code in (401, 403):
            raise ApiError(AUTH) from exc
        if exc.code == 503:
            raise ApiError(BUILDING) from exc
        raise ApiError(SERVER, str(exc.code)) from exc
    except (urllib.error.URLError, ssl.SSLError, OSError) as exc:  # OSError covers timeouts and refused connections
        if tls.is_cert_error(exc):
            raise ApiError(CERT) from exc
        log(f"network error for {path}: {type(exc).__name__}")
        raise ApiError(NETWORK, type(exc).__name__) from exc


class Catalog:
    """One configured catalog: Catalog(base, token, lang). Methods mirror the API."""

    def __init__(self, base=None, token=None, lang=None):
        self.base = cfg.base_url() if base is None else base
        self.token = cfg.token() if token is None else token
        self.lang = cfg.lang() if lang is None else lang

    def _get(self, path, **params):
        return fetch(self.base, self.token, path, params)

    def ping(self):
        return self._get("/v1/ping")

    def letters(self, kind):
        return self._get("/v1/letters", type=kind)

    def titles(self, kind, letter, sort, page, per_page, prefix=None, exact=False):
        """One page of titles; with `prefix` (a-z0-9) the letter is ignored by the API, `exact` keeps only skey == prefix."""
        params = {"type": kind, "letter": letter, "sort": sort, "page": page, "per_page": per_page, "lang": self.lang}
        if prefix:
            params.update(prefix=prefix, exact=1 if exact else None)
        return self._get("/v1/titles", **params)

    def prefixes(self, kind, prefix):
        """{prefix,total,exact,children:[{prefix,n}]} for the titles whose normalized name starts with `prefix`."""
        return self._get("/v1/prefixes", type=kind, prefix=prefix)

    def search(self, query, kind, sort, limit):
        return self._get("/v1/search", q=query, type=kind, sort=sort, limit=limit, lang=self.lang)

    def lists(self):
        return self._get("/v1/lists")

    def tmdb_list(self, kind, key, page, per_page, sort="tmdb"):
        return self._get(
            f"/v1/list/{quote(kind)}/{quote(key)}", page=page, per_page=per_page, sort=sort, lang=self.lang
        )

    def title(self, tt):
        return self._get(f"/v1/title/{check_tt(tt)}", lang=self.lang)

    def seasons(self, tt):
        return self._get(f"/v1/title/{check_tt(tt)}/seasons")

    def episodes(self, tt, season):
        return self._get(f"/v1/title/{check_tt(tt)}/season/{int(season)}", lang=self.lang)

    def poster_url(self, tt, size="w342"):
        """Art URL for Kodi: the service answers 302 to the image; the token has to travel in the query."""
        query = _query({"size": size, "token": self.token or None})
        return f"{cfg.normalize_url(self.base)}/v1/poster/{check_tt(tt)}?{query}"
