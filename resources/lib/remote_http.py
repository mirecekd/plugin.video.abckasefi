# resources/lib/remote_http.py
"""Phone-setup HTTP server: one secret path, one accepted submission, a hard cap on bad requests.

Handlers run in server threads. They never touch the GUI and never call setSetting: they validate the form and
leave the cleaned values in Session.result; the Kodi main thread (remote.py) applies them.
"""
import hmac
import threading
from urllib.parse import parse_qs, urlsplit

from . import remote_page

MAX_BODY = 64 * 1024
MAX_BAD = 30
FORM_TYPE = "application/x-www-form-urlencoded"
CSP = "default-src 'none'; style-src 'unsafe-inline'; form-action 'self'"


class Session:
    """State shared between the server threads and the main thread."""

    def __init__(self, secret, host, current, token_set):
        self.secret = secret
        self.host = host
        self.port = 0
        self.current = current  # settings snapshot taken on the main thread: catalog_url, items_per_page, lang
        self.token_set = token_set
        self.result = None  # cleaned form values of the one accepted submission
        self.finished = threading.Event()  # set after the accepted submission was answered, or at the bad-request cap
        self.server = None
        self._lock = threading.Lock()
        self._bad = 0

    def url(self):
        return f"http://{self.host}:{self.port}/{self.secret}"

    def accept(self, clean):
        """Store the first valid submission; False when one was already accepted."""
        with self._lock:
            if self.result is not None:
                return False
            self.result = clean
        return True

    def record_bad(self):
        with self._lock:
            self._bad += 1
            hit = self._bad == MAX_BAD
        if hit:
            self.finished.set()
            if self.server is not None:
                threading.Thread(target=self._stop_server, daemon=True).start()

    def _stop_server(self):
        if self.server is not None:
            stop_server(self.server)

    @property
    def bad_requests(self):
        return self._bad


def stop_server(server):
    """Shut the server down once serve_forever is really running (shutdown() would block forever before that)."""
    server.running.wait(5)
    server.shutdown()
    server.server_close()


def make_handler(session):
    from http.server import BaseHTTPRequestHandler

    class Handler(BaseHTTPRequestHandler):
        timeout = 10  # seconds; a stalled client must not hold a thread
        server_version = "abckasefi"
        sys_version = ""

        def log_message(self, format, *args):  # the default would write the secret path to the log
            return

        def end_headers(self):
            self.send_header("Cache-Control", "no-store")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", CSP)
            super().end_headers()

        def send_error(self, code, message=None, explain=None):
            session.record_bad()
            super().send_error(code, message, explain)

        def _reply(self, code, page):
            data = page.encode("utf-8")
            self.send_response(code)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Connection", "close")
            self.end_headers()
            self.close_connection = True
            if self.command != "HEAD":
                self.wfile.write(data)

        def _reject(self, code=404):
            session.record_bad()
            self._reply(code, remote_page.message_page("Not found" if code == 404 else "Rejected"))

        def _trusted_origin(self):
            """Host must be our LAN address (DNS rebinding); Origin, when sent, must be us (or 'null', which browsers
            send for a form posted under Referrer-Policy: no-referrer)."""
            host = self.headers.get("Host")
            if host is not None and host not in (session.host, f"{session.host}:{session.port}"):
                return False
            origin = self.headers.get("Origin")
            if origin is None or origin == "null":
                return True
            parts = urlsplit(origin)
            return parts.scheme == "http" and parts.netloc in (session.host, f"{session.host}:{session.port}")

        def _authorized(self):
            expected = f"/{session.secret}".encode()
            given = self.path.encode("utf-8", "replace")
            return hmac.compare_digest(given, expected) and self._trusted_origin() and session.result is None

        def do_GET(self):
            if not self._authorized():
                return self._reject()
            self._reply(200, remote_page.render_form(session.current, session.token_set))

        def do_POST(self):
            if not self._authorized():
                return self._reject()
            if (self.headers.get("Content-Type") or "").split(";")[0].strip().lower() != FORM_TYPE:
                return self._reject(415)
            try:
                length = int(self.headers.get("Content-Length", ""))
            except ValueError:
                return self._reject(411)
            if length < 0 or length > MAX_BODY:
                return self._reject(413)
            try:
                fields = parse_qs(self.rfile.read(length).decode("utf-8"), keep_blank_values=True, max_num_fields=10)
            except (OSError, ValueError):
                return self._reject(400)
            form = {key: values[0] for key, values in fields.items()}
            clean, error = remote_page.validate_form(form)
            if clean is None:
                session.record_bad()
                shown = {key: form.get(key, "") for key in ("catalog_url", "items_per_page", "lang")}
                return self._reply(400, remote_page.render_form(shown, session.token_set, error))
            if not session.accept(clean):
                return self._reject()
            try:
                self._reply(200, remote_page.done_page())
            finally:  # settings are already stored: a phone that drops the connection must not leave the dialog waiting
                session.finished.set()

    for method in ("HEAD", "PUT", "DELETE", "PATCH", "OPTIONS"):
        setattr(Handler, f"do_{method}", Handler._reject)
    return Handler


def start_server(session, host):
    """Bind to (host, random port) and serve in a daemon thread. Raises ImportError when http.server is missing
    (some Android builds) and OSError when the address cannot be bound."""
    from http.server import ThreadingHTTPServer

    class Server(ThreadingHTTPServer):
        daemon_threads = True
        running = threading.Event()  # set by the first serve_forever iteration

        def service_actions(self):
            self.running.set()

        def handle_error(self, request, client_address):  # the default prints a traceback to stderr
            return

    server = Server((host, 0), make_handler(session))
    session.port = server.server_address[1]
    session.server = server
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.2}, daemon=True)
    thread.start()
    return server
