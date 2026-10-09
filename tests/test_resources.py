# tests/test_resources.py
"""Static checks of settings.xml, the two strings.po files and addon.xml against const.py."""
import re
from pathlib import Path

import pytest
from defusedxml import ElementTree as ET

from resources.lib import const, texts

ROOT = Path(__file__).resolve().parent.parent
SETTINGS = ROOT / "resources" / "settings.xml"
PO_FILES = {
    "cs_cz": ROOT / "resources" / "language" / "resource.language.cs_cz" / "strings.po",
    "en_gb": ROOT / "resources" / "language" / "resource.language.en_gb" / "strings.po",
}
SETTING_IDS = {"catalog_url", "api_token", "items_per_page", "lang", "remote_setup", "test_connection"}
CTXT = re.compile(r'^msgctxt "#(\d+)"$')
QUOTED = re.compile(r'^"(.*)"$')


def parse_po(path):
    """Return (ordered list of ids, {id: (msgid, msgstr)}, header text) from a .po file."""
    ids = []
    entries = {}
    header = ""
    current = None
    field = None
    parts = {}
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        match = CTXT.match(line)
        if match:
            current = int(match.group(1))
            ids.append(current)
            parts = {"msgid": "", "msgstr": ""}
            entries[current] = parts
            field = None
        elif line.startswith("msgid "):
            field = "msgid"
            if current is not None:
                parts[field] = line[6:].strip('"')
        elif line.startswith("msgstr "):
            field = "msgstr"
            if current is not None:
                parts[field] = line[7:].strip('"')
            else:
                header = ""
        elif QUOTED.match(line) and field is not None:
            if current is None:
                header += line[1:-1]
            else:
                parts[field] += line[1:-1]
    result = {key: (value["msgid"], value["msgstr"]) for key, value in entries.items()}
    return ids, result, header


def header_of(path):
    """The raw header block (everything before the first msgctxt)."""
    text = path.read_text(encoding="utf-8")
    return text.split("msgctxt", 1)[0]


def const_string_ids():
    return {value for name, value in vars(const).items() if name.startswith("S_") and isinstance(value, int)}


def setting_elements():
    root = ET.parse(SETTINGS).getroot()
    return root, list(root.iter("setting"))


def referenced_label_ids():
    root, settings = setting_elements()
    found = set()
    for element in root.iter():
        for attr in ("label", "help"):
            value = element.get(attr)
            if value:
                found.add(int(value))
    for option in root.iter("option"):
        found.add(int(option.get("label", "0")))
    for heading in root.iter("heading"):
        found.add(int((heading.text or "0").strip()))
    assert settings
    return found


def test_settings_ids_are_exactly_the_documented_ones():
    _, settings = setting_elements()
    ids = [element.get("id") for element in settings]
    assert set(ids) == SETTING_IDS
    assert len(ids) == len(set(ids))


def test_settings_has_one_general_category():
    root, _ = setting_elements()
    categories = list(root.iter("category"))
    assert len(categories) == 1
    assert categories[0].get("label") == str(const.S_CAT_GENERAL)
    assert root.get("version") == "1"


def test_items_per_page_constraints():
    _, settings = setting_elements()
    element = next(s for s in settings if s.get("id") == "items_per_page")
    assert element.get("type") == "integer"
    assert element.findtext("default") == str(const.PER_PAGE_DEFAULT) == "100"
    assert element.findtext("constraints/minimum") == str(const.PER_PAGE_MIN) == "20"
    assert element.findtext("constraints/step") == str(const.PER_PAGE_STEP) == "10"
    assert element.findtext("constraints/maximum") == str(const.PER_PAGE_MAX) == "200"
    control = element.find("control")
    assert control is not None
    assert control.get("type") == "slider"


def test_api_token_is_hidden_and_url_is_not():
    _, settings = setting_elements()
    by_id = {s.get("id"): s for s in settings}
    assert by_id["api_token"].findtext("control/hidden") == "true"
    assert by_id["catalog_url"].find("control/hidden") is None
    assert by_id["catalog_url"].findtext("default") == ""


def test_lang_options_match_const_langs():
    _, settings = setting_elements()
    element = next(s for s in settings if s.get("id") == "lang")
    options = element.findall("constraints/options/option")
    assert [o.text for o in options] == [str(i) for i in range(len(const.LANGS))]
    assert [o.get("label") for o in options] == [str(const.S_LANG_CS), str(const.S_LANG_SK), str(const.S_LANG_EN)]
    assert element.findtext("default") == "0"
    assert const.LANGS == ("cs", "sk", "en")


@pytest.mark.parametrize("setting_id,action", [("remote_setup", "remote_setup"), ("test_connection", "test_connection")])
def test_action_buttons_run_plugin(setting_id, action):
    _, settings = setting_elements()
    element = next(s for s in settings if s.get("id") == setting_id)
    assert element.get("type") == "action"
    assert element.findtext("data") == f"RunPlugin(plugin://{const.ADDON_ID}/?action={action})"
    control = element.find("control")
    assert control is not None
    assert (control.get("type"), control.get("format")) == ("button", "action")


def test_settings_label_and_help_ids_have_labels():
    _, settings = setting_elements()
    for element in settings:
        assert element.get("label"), element.get("id")
        assert element.get("help"), element.get("id")
    used = referenced_label_ids()
    assert const.S_SET_URL in used and const.S_HELP_URL in used and const.S_SET_TOKEN in used
    for name, path in PO_FILES.items():
        _, entries, _ = parse_po(path)
        missing = used - set(entries)
        assert not missing, f"{name} lacks {sorted(missing)}"


@pytest.mark.parametrize("name", sorted(PO_FILES))
def test_every_const_string_has_an_entry(name):
    ids, entries, _ = parse_po(PO_FILES[name])
    wanted = const_string_ids()
    assert len(wanted) >= 50
    assert wanted - set(entries) == set()
    assert set(entries) - wanted == set()
    assert all(msgstr for _, msgstr in entries.values())


@pytest.mark.parametrize("name", sorted(PO_FILES))
def test_no_duplicate_msgctxt(name):
    ids, _, _ = parse_po(PO_FILES[name])
    assert len(ids) == len(set(ids))


def test_po_headers_declare_language_and_utf8():
    for name, path in PO_FILES.items():
        head = header_of(path)
        language = {"cs_cz": "cs_CZ", "en_gb": "en_GB"}[name]
        assert f'"Language: {language}\\n"' in head
        assert "charset=UTF-8" in head


def test_placeholders_match_between_languages():
    _, cs, _ = parse_po(PO_FILES["cs_cz"])
    _, en, _ = parse_po(PO_FILES["en_gb"])
    assert set(cs) == set(en)
    for string_id in en:
        assert cs[string_id][1].count("{}") == en[string_id][1].count("{}"), string_id
        assert en[string_id][0] == cs[string_id][0], string_id
    assert en[const.S_SEASON_N][1].count("{}") == 1
    assert en[const.S_TEST_OK][1].count("{}") == 1
    assert en[const.S_WATCHED_EPS][1].count("{}") == 2


def test_english_po_matches_fallback_table():
    _, en, _ = parse_po(PO_FILES["en_gb"])
    for string_id, text in texts.FALLBACK.items():
        assert en[string_id][1] == text, string_id


def test_czech_texts_are_really_translated():
    _, cs, _ = parse_po(PO_FILES["cs_cz"])
    assert cs[const.S_MOVIES][1] == "Filmy"
    assert cs[const.S_SEASON_N][1] == "{}. série"
    assert cs[const.S_LANG_CS][1] != cs[const.S_LANG_EN][1]


def test_addon_xml_id_matches_const():
    root = ET.parse(ROOT / "addon.xml").getroot()
    assert root.tag == "addon"
    assert root.get("id") == const.ADDON_ID


def test_remote_setup_button_closes_and_saves_the_dialog_first():
    # regression: setSetting called while the settings dialog is open lands in the dialog, which is discarded on cancel
    _, settings = setting_elements()
    element = next(s for s in settings if s.get("id") == "remote_setup")
    assert element.findtext("control/close") == "true"
