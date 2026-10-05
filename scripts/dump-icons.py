"""
List IDA's built-in menu/toolbar icons (SVGs compiled into IDA).

    uv run scripts/dump-icons.py    -> src/icons.txt
                                       .cache/ida_icon_dump.html

Starts the IDA recorded by scripts/link-ida.py in batch mode on a tiny
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
from common.ida import ida_dir, ida_exe
from common.paths import CACHE, ROOT, SRC, file_url, rel
from common.render import write_page

IN_IDA_SCRIPT = os.path.join(ROOT, "scripts", "ida", "dump_icons.py")
OUT = os.path.join(SRC, "icons.txt")
HTML_OUT = os.path.join(CACHE, "ida_icon_dump.html")
WORK_DIR = os.path.join(CACHE, "dump-icons")
STUB_NAME = "stub.bin"
OUT_ENV = "CATPPUCCIN_DUMP_ICONS_OUT"
TIMEOUT_S = 300

# Anything IDA does not recognise loads as a raw binary; all it has to do is
# give IDA a database so the script runs. 15 x nop, ret.
STUB = b"\x90" * 15 + b"\xc3"


def _clean_work_dir(keep=()):
    """Delete everything in WORK_DIR except the names in `keep`."""
    os.makedirs(WORK_DIR, exist_ok=True)
    for name in os.listdir(WORK_DIR):
        if name in keep:
            continue
        path = os.path.join(WORK_DIR, name)
        if os.path.isdir(path):
            shutil.rmtree(path)
        else:
            os.remove(path)


def main():
    exe = ida_exe(ida_dir())

    _clean_work_dir()
    stub = os.path.join(WORK_DIR, STUB_NAME)
    with open(stub, "wb") as f:
        f.write(STUB)
    try:
        dump = os.path.join(WORK_DIR, "dump")
        os.makedirs(dump)
        env = dict(os.environ, **{OUT_ENV: dump})
        print("running %s ..." % exe)
        try:
            subprocess.run([exe, "-A", "-S" + IN_IDA_SCRIPT, stub],
                           cwd=WORK_DIR, env=env, timeout=TIMEOUT_S, check=False)
        except subprocess.TimeoutExpired:
            raise ScriptError("IDA did not finish within %d s" % TIMEOUT_S)

        error = os.path.join(dump, "error.txt")
        if os.path.isfile(error):
            with open(error, encoding="utf-8") as f:
                raise ScriptError("inside IDA:\n" + f.read())
        listing = os.path.join(dump, "icons.txt")
        if not os.path.isfile(listing):
            raise ScriptError("IDA exited without listing the icons")
        with open(listing, encoding="utf-8") as f:
            names = [n for n in f.read().split("\n") if n]
        if not names:
            raise ScriptError("IDA listed no icons")

        with open(OUT, "w", encoding="utf-8", newline="\n") as f:
            f.write("".join(n + "\n" for n in names))
        print("listed %d icons in %s" % (len(names), rel(OUT)))

        write_page([(n, os.path.join(dump, "svg", n)) for n in names],
                   "IDA's built-in icons", HTML_OUT)
        print("rendered them to %s" % file_url(HTML_OUT))
    finally:
        _clean_work_dir(keep=(STUB_NAME,))


if __name__ == "__main__":
    run(main, "dump-icons")
