"""
Dump the icons IDA's actions can show.

    uv run scripts/dump-icons.py    -> src/ida/icon_meta.yaml
                                       .cache/ida-icon-dump/

Starts IDA (common.paths.ida_dir()) headless on a tiny throwaway binary, with
the catppuccin plugin off (CATPPUCCIN_DISABLE=1); scripts/ida/dump_icons.py
writes the icons inside IDA and quits. See that script for the output.

The binary lives at a fixed path, .cache/dump-icons/stub.bin, so IDA's
recent-files history gets one entry rather than one per run. That folder is
emptied before each run (so IDA never reopens an old database) and afterwards
only the stub is kept.
"""

import os
import shutil
import subprocess

from common.errors import ScriptError, run
from common.paths import DUMP_ICONS_WORK_DIR, ICON_DUMP_DIR, ICON_META_FILE, IDA_DUMP_SCRIPT, ida_dir, ida_exe, rel

STUB_NAME = "stub.bin"
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
        print("running %s ..." % exe)
        try:
            subprocess.run([exe, "-A", "-S%s" % IDA_DUMP_SCRIPT, stub], cwd=DUMP_ICONS_WORK_DIR,
                           env=dict(os.environ, CATPPUCCIN_DISABLE="1"), timeout=TIMEOUT_S, check=False)
        except subprocess.TimeoutExpired:
            raise ScriptError("IDA did not finish within %d s" % TIMEOUT_S)
    finally:
        _clean_work_dir(keep=(STUB_NAME,))

    error = ICON_DUMP_DIR / "error.txt"
    if error.is_file():
        raise ScriptError("inside IDA:\n" + error.read_text(encoding="utf-8"))
    summary = ICON_DUMP_DIR / "summary.txt"
    if not summary.is_file():
        raise ScriptError("IDA exited without dumping the icons")
    print(summary.read_text(encoding="utf-8").rstrip())
    print("wrote %s; copies of the icons in %s" % (rel(ICON_META_FILE), rel(ICON_DUMP_DIR)))


if __name__ == "__main__":
    run(main)
