# resources/lib/tls.py
"""TLS policy: certificate verification is ALWAYS on. There is deliberately no switch to turn it off."""
import ssl

from .const import S_ERR_CERT


def ssl_context():
    """Verifying context. Prefer the CA bundle of script.module.certifi (Kodi builds often lack a system store)."""
    try:
        import certifi
        return ssl.create_default_context(cafile=certifi.where())
    except (ImportError, OSError):
        return ssl.create_default_context()


def is_cert_error(exc):
    """True when `exc` (or its reason) is a certificate verification failure."""
    reason = getattr(exc, "reason", exc)
    return isinstance(reason, ssl.SSLCertVerificationError) or isinstance(exc, ssl.SSLCertVerificationError)


CERT_MESSAGE_ID = S_ERR_CERT
