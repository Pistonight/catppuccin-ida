"""
Research probe, run inside IDA (File > Script file... / Alt+F7): which action
is behind a menu entry? For each text in LABELS, lists every registered
action whose label matches (name, label, icon id and its icon table path,
tooltip), and every menu entry with that text (menu path, submenu or not).

Edit LABELS, then run. Writes .cache/action_labels_probe.txt.
"""

import traceback
from pathlib import Path

import ida_kernwin
from PySide6.QtCore import QDirIterator
from PySide6.QtWidgets import QApplication, QMainWindow

LABELS = ["Disassembly"]

ROOT = Path(__file__).resolve().parents[2]
OUT = ROOT / ".cache" / "action_labels_probe.txt"

lines = []


def log(*args):
    lines.append(" ".join(str(a) for a in args))


def menu_text(value):
    """A label without Qt's & and IDA's ~ mnemonic marks (~D~isassembly) and
    the tab-separated shortcut."""
    value = value.split("\t")[0].replace("~", "")
    return value.replace("&&", "\0").replace("&", "").replace("\0", "&").strip()


def icon_table():
    """{id: path} for IDA's icon table."""
    table = {}
    it = QDirIterator(":/", QDirIterator.IteratorFlag.Subdirectories)
    while it.hasNext():
        resource = it.next()
        parts = resource[len(":/"):].split("/", 1)
        if len(parts) == 2 and resource.endswith((".svg", ".png")):
            icon_id = ida_kernwin.get_icon_id_by_name(parts[1])
            if icon_id >= 0:
                table.setdefault(icon_id, parts[1])
    return table


try:
    table = icon_table()
    wanted = {label.lower() for label in LABELS}

    log("== actions whose label matches %s" % LABELS)
    for action in sorted(ida_kernwin.get_registered_actions()):
        label = menu_text(ida_kernwin.get_action_label(action) or "")
        if label.lower() in wanted:
            ok, icon_id = ida_kernwin.get_action_icon(action)
            log("  %s: label=%r icon=#%s %s tooltip=%r"
                % (action, label, icon_id if ok else "-", table.get(icon_id, "(not in the icon table)") if ok else "",
                   ida_kernwin.get_action_tooltip(action) or ""))

    log("")
    log("== menu entries with that text (menus opened as if clicked)")
    opened = set()

    def walk(menu, where):
        if menu is None or id(menu) in opened:
            return
        opened.add(id(menu))
        menu.aboutToShow.emit()
        QApplication.processEvents()
        for entry in menu.actions():
            text = menu_text(entry.text())
            if text.lower() in wanted:
                log("  %s > %s: submenu=%s objectName=%r data=%r"
                    % (where, text, entry.menu() is not None, entry.objectName(), entry.data()))
            walk(entry.menu(), where + " > " + text)
        menu.aboutToHide.emit()

    for w in QApplication.topLevelWidgets():
        if isinstance(w, QMainWindow):
            for entry in w.menuBar().actions():
                walk(entry.menu(), menu_text(entry.text()))
except Exception:
    log(traceback.format_exc())

OUT.parent.mkdir(parents=True, exist_ok=True)
OUT.write_text("\n".join(lines) + "\n", encoding="utf-8")
print("action labels probe: wrote %s (%d lines)" % (OUT, len(lines)))
