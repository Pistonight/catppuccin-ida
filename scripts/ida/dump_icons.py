"""
Runs inside IDA (started by scripts/dump-icons.py): dump IDA's built-in
menu/toolbar icons (Qt resources) into the folder $CATPPUCCIN_DUMP_ICONS_OUT,
then quit. Numbered icons (e.g. 177.svg) are skipped: IDA looks those up by
number, and a theme cannot replace them.

    icons.txt   the icon file names, one per line
    svg/        the icons themselves
    error.txt   a traceback, if something failed
"""

import os
import traceback

import ida_pro
from PySide6.QtCore import QDirIterator, QFile, QIODevice

PREFIX = ":/IDAG/resources/menu/"

out_dir = os.environ["CATPPUCCIN_DUMP_ICONS_OUT"]
try:
    svg_dir = os.path.join(out_dir, "svg")
    os.makedirs(svg_dir, exist_ok=True)
    names = []
    it = QDirIterator(PREFIX, QDirIterator.IteratorFlag.Subdirectories)
    while it.hasNext():
        path = it.next()
        if not path.endswith(".svg"):
            continue
        name = path[len(PREFIX):]
        if name[:-len(".svg")].isdigit():
            continue
        names.append(name)
        f = QFile(path)
        f.open(QIODevice.OpenModeFlag.ReadOnly)
        with open(os.path.join(svg_dir, name), "wb") as out:
            out.write(f.readAll().data())
    with open(os.path.join(out_dir, "icons.txt"), "w", encoding="utf-8", newline="\n") as f:
        f.write("".join(n + "\n" for n in sorted(names)))
except Exception:
    with open(os.path.join(out_dir, "error.txt"), "w", encoding="utf-8") as f:
        f.write(traceback.format_exc())
finally:
    ida_pro.qexit(0)
