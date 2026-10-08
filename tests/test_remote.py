# tests/test_remote.py
"""Phone setup form: GET and POST against the real HTTP server on 127.0.0.1 (validation, escaping, one-shot accept)."""
# ruff: noqa: S105, S106, F401, F811  (fixture tokens are test data; fixtures are imported by name)
import threading

import pytest

from resources.lib import cfg, const, remote, remote_http, remote_page

from .remote_support import HOST, SECRET, good, post, request, server, settings


def test_get_with_secret_serves_prefilled_form_without_the_stored_token(server):
    status, body, resp = request(server, "GET")
    assert status == 200
    assert 'value="http://nas.lan:8090"' in body and 'value="100"' in body
    assert '<option value="sk" selected>' in body
    assert 'type="password"' in body and "STORED-TOKEN-123" not in body
    assert "set - leave empty to keep" in body
    assert resp.getheader("Cache-Control") == "no-store" and resp.getheader("Referrer-Policy") == "no-referrer"


def test_no_hint_when_no_token_is_stored(settings):
    settings.store["api_token"] = ""
    session = remote_http.Session("x" * 22, HOST, remote.settings_snapshot(), bool(cfg.token()))
    assert "set - leave empty" not in remote_page.render_form(session.current, session.token_set)


@pytest.mark.parametrize("path", ["/wrong", "/", f"/{SECRET[:-1]}", f"/{SECRET}x", f"/{SECRET}/x"])
def test_wrong_path_is_404_with_security_headers(server, path):
    status, body, resp = request(server, "GET", path)
    assert status == 404 and "STORED" not in body and "S3cret" not in body
    assert resp.getheader("Cache-Control") == "no-store" and resp.getheader("Referrer-Policy") == "no-referrer"


@pytest.mark.parametrize("method", ["PUT", "DELETE", "HEAD", "OPTIONS", "PATCH"])
def test_other_methods_are_404(server, method):
    assert request(server, method)[0] == 404


def test_foreign_host_header_is_refused(server):
    assert request(server, "GET", headers={"Host": "evil.example"})[0] == 404


def test_foreign_origin_is_refused_on_post_and_own_origin_accepted(server):
    status, _body, _ = post(server, good(), headers={"Origin": "http://evil.example"})
    assert status == 404 and server.result is None
    assert post(server, good(), headers={"Origin": f"http://{HOST}:{server.port}"})[0] == 200


def test_valid_post_is_accepted_once_and_not_stored_by_the_handler(server, settings):
    status, body, _ = post(server, good(api_token="NEW-token_9"))
    assert status == 200 and "Saved" in body
    assert server.finished.wait(2)
    assert settings.writers == [] and settings.store["catalog_url"] == "http://nas.lan:8090"
    assert server.result == {"catalog_url": "https://cat.example.org", "api_token": "NEW-token_9",
                             "items_per_page": 50, "lang": const.LANGS.index("en")}
    remote.apply_result(server.result)
    assert settings.store == {"catalog_url": "https://cat.example.org", "api_token": "NEW-token_9",
                              "items_per_page": "50", "lang": "2"}
    assert settings.writers == [threading.current_thread()] * 4


def test_second_post_is_rejected_and_first_result_kept(server):
    assert post(server, good())[0] == 200
    assert post(server, good(catalog_url="http://other.example"))[0] == 404
    assert server.result is not None and server.result["catalog_url"] == "https://cat.example.org"
    assert request(server, "GET")[0] == 404


def test_empty_token_keeps_the_stored_one(server, settings):
    post(server, good(api_token="   "))
    assert server.result is not None and server.result["api_token"] is None
    remote.apply_result(server.result)
    assert settings.store["api_token"] == "STORED-TOKEN-123"


@pytest.mark.parametrize("bad_url", ["ftp://host/x", "javascript:alert(1)", "http://user:pw@host:8090", "http://", "host.lan",
                                     "", "http://h/?token=1", "https://" + "a" * 600])
def test_invalid_url_rerenders_the_form_and_stores_nothing(server, settings, bad_url):
    status, body, _ = post(server, good(catalog_url=bad_url, api_token="SHOULD-NOT-ECHO"))
    assert status == 400 and 'class="err"' in body and "http:// or https://" in body
    assert "SHOULD-NOT-ECHO" not in body
    assert server.result is None and settings.writers == []
    assert request(server, "GET")[0] == 200  # still usable after a mistake


def test_token_with_a_space_is_rejected(server):
    status, body, _ = post(server, good(api_token="abc def"))
    assert status == 400 and "Invalid input" in body and "abc def" not in body
    assert server.result is None


@pytest.mark.parametrize("bad", ["abc", "-5", "", "1e3", "20.5"])
def test_non_integer_per_page_is_rejected(server, bad):
    assert post(server, good(items_per_page=bad))[0] == 400 and server.result is None


def test_bad_language_and_missing_fields_are_rejected(server):
    assert post(server, good(lang="de"))[0] == 400 and server.result is None
    assert post(server, {"catalog_url": "http://a.lan"})[0] == 400


def test_per_page_9999_is_clamped_to_200_and_small_values_to_20(server):
    assert post(server, good(items_per_page="9999"))[0] == 200
    assert server.result is not None and server.result["items_per_page"] == 200
    cleaned, _error = remote_page.validate_form(good(items_per_page="3"))
    assert cleaned is not None and cleaned["items_per_page"] == 20


def test_hostile_values_are_html_escaped_on_rerender(server):
    hostile = '"><script>alert(1)</script>'
    status, body, _ = post(server, good(catalog_url=hostile, items_per_page=hostile, lang=hostile))
    assert status == 400
    assert "<script>" not in body and "&lt;script&gt;" in body and "&quot;&gt;" in body
