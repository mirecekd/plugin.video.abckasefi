# resources/lib/remote.py
"""Configure the add-on from a phone: a one-time web form behind a QR code (action=remote_setup).

The HTTP server (remote_http) runs in daemon threads and only validates. All Kodi GUI work and every setSetting call
happens here, on the main thread.
"""
import base64
import contextlib
import os
import socket
import time

import xbmc
import xbmcgui

from . import cfg, const, log, remote_page, remote_ui
from .remote_http import Session, start_server, stop_server


def usable_ip(address):
    return bool(address) and not address.startswith(("127.", "169.254.", "0."))


def lan_ip():
    """This device's LAN address: routing-table lookup through a UDP socket (nothing is sent), then Kodi's own idea."""
    with contextlib.suppress(OSError), socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
        probe.connect(("10.255.255.255", 1))
        address = probe.getsockname()[0]
        if usable_ip(address):
            return address
    address = xbmc.getIPAddress()
    return address if usable_ip(address) else ""


def notify(message):
    xbmcgui.Dialog().notification(remote_page.text(const.S_ADDON_NAME), message, xbmcgui.NOTIFICATION_INFO, 4000)


def new_secret():
    return base64.urlsafe_b64encode(os.urandom(16)).rstrip(b"=").decode()


def settings_snapshot():
    return {"catalog_url": cfg.base_url(), "items_per_page": str(cfg.per_page()), "lang": cfg.lang()}


def apply_result(clean):
    """Store the validated values. Main thread only; an absent token keeps the stored one."""
    cfg.put("catalog_url", clean["catalog_url"])
    if clean["api_token"] is not None:
        cfg.put("api_token", clean["api_token"])
    cfg.put("items_per_page", clean["items_per_page"])
    cfg.put("lang", clean["lang"])


def wait_for_finish(session, dialog, timeout, monitor):
    """Block the main thread until submit, dialog closed, bad-request cap, timeout or Kodi abort."""
    deadline = time.monotonic() + timeout
    while not session.finished.is_set() and not dialog.closed and time.monotonic() < deadline:
        if monitor.waitForAbort(0.5):
            break


def run(bind_host=None, make_png=None, timeout=const.REMOTE_TIMEOUT):
    """Show the QR code and wait for the phone. `bind_host` and `make_png` exist so tests can avoid the network."""
    host = bind_host or lan_ip()
    if not host:
        notify(remote_page.text(const.S_RM_NO_NETWORK))
        return False
    session = Session(new_secret(), host, settings_snapshot(), bool(cfg.token()))
    try:
        server = start_server(session, host)
    except ImportError:
        notify(remote_page.text(const.S_RM_NO_SERVER))
        return False
    except OSError:
        notify(remote_page.text(const.S_RM_NO_NETWORK))
        return False
    run_id = base64.urlsafe_b64encode(os.urandom(6)).decode()
    files = []
    dialog = None
    closed_by_user = False
    try:
        qr_path = remote_ui.temp_file(run_id, "qr", (make_png or remote_ui.qr_png)(session.url()))
        files.append(qr_path)
        background = remote_ui.temp_file(run_id, "bg", remote_ui.white_png())
        files.append(background)
        dialog = remote_ui.QrDialog(background, qr_path, session.url())
        dialog.show()
        log.log(f"remote setup listening on port {session.port}")
        wait_for_finish(session, dialog, timeout, xbmc.Monitor())
        closed_by_user = dialog.closed
    finally:
        if dialog is not None:
            dialog.close()
        stop_server(server)
        remote_ui.remove_files(files)
    if session.result is not None:
        apply_result(session.result)
        notify(remote_page.text(const.S_RM_SAVED))
        return True
    if not closed_by_user:
        notify(remote_page.text(const.S_RM_TIMEOUT))
    return False
