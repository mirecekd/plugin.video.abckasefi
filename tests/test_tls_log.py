# tests/test_tls_log.py
"""TLS policy (verification can never be disabled) and log masking."""
import pathlib
import ssl

from resources.lib import log, tls


def test_ssl_context_always_verifies_certificates():
    ctx = tls.ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True


def test_ssl_context_falls_back_to_a_verifying_default_without_certifi(monkeypatch):
    import builtins
    real_import = builtins.__import__

    def no_certifi(name, *a, **k):
        if name == "certifi":
            raise ImportError(name)
        return real_import(name, *a, **k)

    monkeypatch.setattr(builtins, "__import__", no_certifi)
    ctx = tls.ssl_context()
    assert ctx.verify_mode == ssl.CERT_REQUIRED and ctx.check_hostname is True


def test_no_module_ever_disables_verification():
    banned = ("_create_unverified_context", "CERT_NONE", "verify=False", "check_hostname = False", "check_hostname=False")
    root = pathlib.Path(__file__).resolve().parent.parent
    sources = list((root / "resources").rglob("*.py")) + [root / "default.py"]
    assert len(sources) > 10, "the scan found too few files to mean anything"
    for path in sources:
        text = path.read_text(encoding="utf-8")
        for needle in banned:
            assert needle not in text, f"{path} contains {needle}"


def test_secrets_are_masked_in_log_lines():
    line = log.log("GET http://h:8090/v1/ping?token=SeCrEt123&x=1 Bearer abcDEF123 /Xk3_9aB-c2D4eF6gH8iJkQ/ end")
    for leaked in ("SeCrEt123", "abcDEF123", "Xk3_9aB-c2D4eF6gH8iJkQ"):
        assert leaked not in line
    assert "token=***" in line
