"""
List IDA's built-in menu/toolbar icons (SVGs compiled into IDA).

    uv run scripts/dump-icons.py    -> src/icons.txt
                                       .cache/ida_icon_dump.html

Starts IDA (common.paths.ida_dir()) in batch mode on a tiny
throwaway binary; scripts/ida/dump_icons.py dumps the icons inside IDA.
src/icons.txt gets the icon file names; .cache/ida_icon_dump.html renders
the original icons for reference. Numbered icons (e.g. 177.svg) are left out,
since a theme cannot replace them.

The binary lives at a fixed path, .cache/dump-icons/stub.bin, so IDA's
recent-files history gets one entry rather than one per run. That folder is
emptied before each run (so IDA never reopens an old database) and afterwards
only the stub is kept.

The icons are all 32x32 (viewBox="0 0 32 32").
"""

import os
import shutil
import subprocess

from common.errors import ScriptError, run
from common.paths import (DUMP_ICONS_WORK_DIR, ICON_DUMP_PREVIEW, ICON_LIST, IDA_DUMP_SCRIPT, file_url,
                          ida_dir, ida_exe, rel)
from common.render import write_page

STUB_NAME = "stub.bin"
OUT_ENV = "CATPPUCCIN_DUMP_ICONS_OUT"
TIMEOUT_S = 300

# Anything IDA does not recognise loads as a raw binary; all it has to do is
# give IDA a database so the script runs. 15 x nop, ret.
STUB = b"\x90" * 15 + b"\xc3"


def _clean_work_dir(keep=()):
    """Delete everything in DUMP_ICONS_WORK_DIR except the names in `keep`."""
    DUMP_ICONS_WORK_DIR.mkdir(parents=True, exist_ok=True)
    for path in DUMP_ICONS_WORK_DIR.iterdir():
        if path.name in keep:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


def main():
    exe = ida_exe(ida_dir())

    _clean_work_dir()
    stub = DUMP_ICONS_WORK_DIR / STUB_NAME
    stub.write_bytes(STUB)
    try:
        dump = DUMP_ICONS_WORK_DIR / "dump"
        dump.mkdir()
        env = dict(os.environ, **{OUT_ENV: str(dump)})
        print("running %s ..." % exe)
        try:
            subprocess.run([exe, "-A", "-S%s" % IDA_DUMP_SCRIPT, stub],
                           cwd=DUMP_ICONS_WORK_DIR, env=env, timeout=TIMEOUT_S, check=False)
        except subprocess.TimeoutExpired:
            raise ScriptError("IDA did not finish within %d s" % TIMEOUT_S)

        error = dump / "error.txt"
        if error.is_file():
            raise ScriptError("inside IDA:\n" + error.read_text(encoding="utf-8"))
        listing = dump / "icons.txt"
        if not listing.is_file():
            raise ScriptError("IDA exited without listing the icons")
        names = [n for n in listing.read_text(encoding="utf-8").split("\n") if n]
        if not names:
            raise ScriptError("IDA listed no icons")

        ICON_LIST.write_text("".join(n + "\n" for n in names), encoding="utf-8", newline="\n")
        print("listed %d icons in %s" % (len(names), rel(ICON_LIST)))

        write_page([(n, dump / "svg" / n) for n in names],
                   "IDA's built-in icons", ICON_DUMP_PREVIEW)
        print("rendered them to %s" % file_url(ICON_DUMP_PREVIEW))
    finally:
        _clean_work_dir(keep=(STUB_NAME,))


if __name__ == "__main__":
    run(main)
