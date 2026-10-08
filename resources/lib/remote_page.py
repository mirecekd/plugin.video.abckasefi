# resources/lib/remote_page.py
"""Phone setup page: HTML form rendering and server-side validation of the submitted values."""
import html
import re

from . import cfg, const
from .texts import t

DEFAULTS = {
    const.S_RM_TITLE: "Configure from phone",
    const.S_RM_SCAN: "Scan this QR code with your phone",
    const.S_RM_OPEN: "or open this address in a browser on the same network",
    const.S_RM_SAVED: "Settings saved",
    const.S_RM_TIMEOUT: "Phone setup ended without saving",
    const.S_RM_NO_NETWORK: "No local network address found",
    const.S_RM_NO_SERVER: "This device cannot run the setup server",
    const.S_RM_SAVE: "Save",
    const.S_RM_KEEP_TOKEN: "set - leave empty to keep",
    const.S_RM_DONE_PAGE: "Saved. You can close this page.",
    const.S_SET_URL: "Catalog address",
    const.S_SET_TOKEN: "API token",
    const.S_SET_PER_PAGE: "Items per page",
    const.S_SET_LANG: "Language",
}
LANG_NAMES = {"cs": "Čeština", "sk": "Slovenčina", "en": "English"}
_DIGITS = re.compile(r"^[0-9]{1,6}$")

_STYLE = ("body{font-family:sans-serif;margin:1em;max-width:30em}label{display:block;margin-top:1em}"
          "input,select,button{width:100%;font-size:1.1em;padding:.4em;box-sizing:border-box}"
          ".err{color:#b00020;font-weight:bold}")


def text(string_id):
    """Localized text, or the English default when the add-on has no translation (Kodi then returns the bare id)."""
    value = t(string_id)
    return DEFAULTS.get(string_id, value) if value == str(string_id) else value


def _esc(value):
    return html.escape(str(value), quote=True)


def _page(body):
    return ("<!DOCTYPE html><html><head><meta charset=\"utf-8\"><meta name=\"referrer\" content=\"no-referrer\">"
            "<meta name=\"viewport\" content=\"width=device-width,initial-scale=1\">"
            f"<title>{_esc(text(const.S_RM_TITLE))}</title><style>{_STYLE}</style></head><body>{body}</body></html>")


def done_page():
    return _page(f"<h2>{_esc(text(const.S_RM_DONE_PAGE))}</h2>")


def message_page(message):
    return _page(f"<h2>{_esc(message)}</h2>")


def render_form(values, token_set, error=""):
    """Form pre-filled from `values` (catalog_url, items_per_page, lang). The token is never pre-filled."""
    options = "".join(
        f"<option value=\"{code}\"{' selected' if code == values.get('lang') else ''}>{_esc(LANG_NAMES[code])}</option>"
        for code in const.LANGS)
    hint = f" placeholder=\"{_esc(text(const.S_RM_KEEP_TOKEN))}\"" if token_set else ""
    error_html = f"<p class=\"err\">{_esc(error)}</p>" if error else ""
    body = (
        f"<h2>{_esc(text(const.S_RM_TITLE))}</h2>{error_html}<form method=\"post\" autocomplete=\"off\">"
        f"<label>{_esc(text(const.S_SET_URL))}<input name=\"catalog_url\" type=\"text\" maxlength=\"{cfg.MAX_URL}\""
        f" value=\"{_esc(values.get('catalog_url', ''))}\"></label>"
        f"<label>{_esc(text(const.S_SET_TOKEN))}<input name=\"api_token\" type=\"password\" maxlength=\"256\""
        f" autocomplete=\"new-password\"{hint}></label>"
        f"<label>{_esc(text(const.S_SET_PER_PAGE))}<input name=\"items_per_page\" type=\"number\""
        f" min=\"{const.PER_PAGE_MIN}\" max=\"{const.PER_PAGE_MAX}\" step=\"{const.PER_PAGE_STEP}\""
        f" value=\"{_esc(values.get('items_per_page', ''))}\"></label>"
        f"<label>{_esc(text(const.S_SET_LANG))}<select name=\"lang\">{options}</select></label>"
        f"<p><button type=\"submit\">{_esc(text(const.S_RM_SAVE))}</button></p></form>")
    return _page(body)


def validate_form(form):
    """(clean, error). `form` maps field -> str. clean = catalog_url, api_token (None = keep the stored one),
    items_per_page (int), lang (index into const.LANGS); clean is None when error is set."""
    url = cfg.normalize_url(form.get("catalog_url", ""))
    if not cfg.validate_url(url)[0]:
        return None, text(const.S_ERR_BAD_URL)
    token_ok, token = cfg.validate_token(form.get("api_token", ""))
    per_page = form.get("items_per_page", "").strip()
    lang = form.get("lang", "")
    if not token_ok or not _DIGITS.match(per_page) or lang not in const.LANGS:
        return None, text(const.S_ERR_BAD_INPUT)
    clean = {"catalog_url": url, "api_token": token or None,
             "items_per_page": cfg.clamp_per_page(per_page), "lang": const.LANGS.index(lang)}
    return clean, ""
