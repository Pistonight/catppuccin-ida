"""The icons IDA's actions show: src/ida/icon_meta.yaml (from dump-icons)."""

from typing import NamedTuple

import yaml

from common.errors import ScriptError
from common.paths import ICON_META_FILE, rel

HINT = " (run ./x dump-icons)"


class Icon(NamedTuple):
    path: str               # the theme's version, under themes/catppuccin/
    actions: tuple          # the actions showing it when dumped
    map_by_action: bool     # the plugin matches the actions, not the path


def load_icon_meta():
    """[Icon] in file order."""
    if not ICON_META_FILE.is_file():
        raise ScriptError("missing %s%s" % (rel(ICON_META_FILE), HINT))
    with ICON_META_FILE.open(encoding="utf-8") as f:
        entries = yaml.safe_load(f)
    if not isinstance(entries, list):
        raise ScriptError("%s: expected a list of icons%s" % (rel(ICON_META_FILE), HINT))
    icons = []
    for i, entry in enumerate(entries):
        if not isinstance(entry, dict) or not isinstance(entry.get("path"), str) \
                or not isinstance(entry.get("actions"), list) \
                or not isinstance(entry.get("map_by_action", False), bool):
            raise ScriptError("%s: entry %d: expected a `path`, an `actions` list and optionally "
                              "`map_by_action: true`%s" % (rel(ICON_META_FILE), i + 1, HINT))
        icons.append(Icon(entry["path"], tuple(str(a) for a in entry["actions"]),
                          entry.get("map_by_action", False)))
    return icons
