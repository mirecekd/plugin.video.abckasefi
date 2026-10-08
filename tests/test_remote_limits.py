# tests/test_remote_limits.py
"""Phone setup hardening: content type, body size, bad-request cap, secret handling, log silence."""
# ruff: noqa: F401, F811  (fixtures are imported by name)
import http.client
import socket
import time
from urllib.parse import urlencode

import pytest

from resources.lib import log, remote, remote_http

from .remote_support import (
    FORM,
    HOST,
    env,
    good,
    post,
    press,
    request,
    server,
    settings,
    start_run,
    url_parts,
)


def test_wrong_content_type_is_rejected(server):
    data = urlencode(good())
    for ctype in ("application/json", "multipart/form-data; boundary=x", "text/plain"):
        assert request(server, "POST", body=data, headers={"Content-Type": ctype})[0] == 415
    assert request(server, "POST", body=data)[0] == 415
    assert server.result is None


def test_charset_parameter_on_the_form_type_is_fine(server):
    assert post(server, good(), headers={"Content-Type": FORM + "; charset=UTF-8"})[0] == 200


def _raw_post(server, length=None):
    conn = http.client.HTTPConnection(HOST, server.port, timeout=5)
    conn.putrequest("POST", f"/{server.secret}")
    conn.putheader("Content-Type", FORM)
    if length is not None:
        conn.putheader("Content-Length", str(length))
    conn.endheaders()
    resp = conn.getresponse()
    conn.close()
    return resp.status


def test_oversized_declared_length_is_413_and_missing_length_is_411(server):
    assert _raw_post(server, remote_http.MAX_BODY + 1) == 413
    assert _raw_post(server) == 411
    assert server.result is None


def test_really_oversized_body_never_gets_accepted(server):
    body = urlencode(good(catalog_url="http://a.lan/" + "x" * remote_http.MAX_BODY))
    try:
        status = request(server, "POST", body=body, headers={"Content-Type": FORM})[0]
    except OSError:  # the server may reset the connection while the client is still sending
        status = 413
    assert status == 413 and server.result is None


def test_thirty_bad_requests_stop_the_server(server):
    for _ in range(remote_http.MAX_BAD):
        assert request(server, "GET", "/nope")[0] == 404
    assert server.finished.wait(2)
    deadline = time.monotonic() + 3
    while time.monotonic() < deadline:
        try:
            socket.create_connection((HOST, server.port), timeout=0.5).close()
        except OSError:
            return
        time.sleep(0.05)
    pytest.fail("server still accepts connections after 30 bad requests")


def test_invalid_submissions_count_as_bad_requests(server):
    for _ in range(5):
        post(server, good(lang="xx"))
    assert server.bad_requests == 5


def test_29_bad_requests_leave_the_server_running(server):
    for _ in range(remote_http.MAX_BAD - 1):
        request(server, "GET", "/nope")
    assert not server.finished.is_set() and request(server, "GET")[0] == 200


def test_secret_never_reaches_the_log_or_stderr(env, monkeypatch, capfd, caplog):
    lines = []
    monkeypatch.setattr(log.xbmc, "log", lambda line, level=None: lines.append(line))
    thread, _out, urls = start_run(env, timeout=2)
    port, secret = url_parts(urls[0])
    probe = type("Probe", (), {"port": port, "secret": secret})
    request(probe, "GET")
    request(probe, "GET", "/other")
    request(probe, "POST", body="x", headers={"Content-Type": "text/plain"})
    press(env.dialogs[0], 92)
    thread.join(5)
    captured = capfd.readouterr()
    assert lines, "run() should log something"
    assert secret not in "\n".join(lines) and secret not in captured.out + captured.err and secret not in caplog.text
    assert secret not in "\n".join(str(n) for n in env.notes)


def test_handler_overrides_log_message_to_a_noop(server, capfd):
    request(server, "GET")
    request(server, "GET", "/zzz")
    assert server.secret not in capfd.readouterr().err
    handler = remote_http.make_handler(server)
    assert "log_message" in vars(handler)
    assert handler.log_message(None, "%s", server.secret) is None  # type: ignore[arg-type]


def test_secret_comparison_uses_hmac_compare_digest(server, monkeypatch):
    calls = []
    real = remote_http.hmac.compare_digest
    monkeypatch.setattr(remote_http.hmac, "compare_digest", lambda a, b: calls.append((a, b)) or real(a, b))
    assert request(server, "GET")[0] == 200
    assert calls and calls[0][1] == f"/{server.secret}".encode()


def test_new_secret_is_url_safe_unique_and_unpadded():
    secrets = {remote.new_secret() for _ in range(50)}
    assert len(secrets) == 50 and all(len(s) == 22 and not set("=/+") & set(s) for s in secrets)
