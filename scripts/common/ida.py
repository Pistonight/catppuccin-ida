"""Locating the IDA installation.

scripts/link-ida.py finds IDA and records it in .cache/IDA_LOCATION.txt;
other scripts read it back with ida_dir().
"""

import os
import re
import sys

from common.errors import ScriptError
from common.paths import CACHE

INSTALL_RE = re.compile(r"IDA Professional (\d+(?:\.\d+)*)$")
LOCATION_FILE_NAME = "IDA_LOCATION.txt"


def find_install():
    """The highest-versioned IDA Professional under Program Files, or None."""
    drive = os.environ.get("SYSTEMDRIVE", "C:")
    program_files = os.path.join(drive + os.sep, "Program Files")
    try:
        entries = os.listdir(program_files)
    except OSError:
        return None
    found = []
    for name in entries:
        m = INSTALL_RE.match(name)
        path = os.path.join(program_files, name)
        if m and os.path.isdir(path):
            found.append((tuple(int(p) for p in m.group(1).split(".")), path))
    return max(found)[1] if found else None


def check_install(ida_dir):
    """The install's IDAPython dir; raises ScriptError if it is not usable."""
    if not os.path.isfile(os.path.join(ida_dir, "ida.dll")):
        raise ScriptError("%s is not a usable IDA install (missing ida.dll)" % ida_dir)
    # 9.0 keeps the modules in python/3/, later versions in python/
    for python_dir in (os.path.join(ida_dir, "python"), os.path.join(ida_dir, "python", "3")):
        if os.path.isfile(os.path.join(python_dir, "ida_idaapi.py")):
            return python_dir
    raise ScriptError("%s is not a usable IDA install (no IDAPython modules in python/)" % ida_dir)


def location_file():
    """.cache/IDA_LOCATION.txt"""
    return os.path.join(CACHE, LOCATION_FILE_NAME)


def ida_dir():
    """The IDA install recorded by link-ida (checked to still be usable)."""
    path = location_file()
    if not os.path.isfile(path):
        raise ScriptError("IDA location unknown; run ./x link-ida first")
    with open(path, encoding="utf-8") as f:
        location = f.read().strip()
    check_install(location)
    return location


def ida_exe(location):
    """The IDA GUI executable of an install."""
    exe = os.path.join(location, "ida.exe" if sys.platform == "win32" else "ida")
    if not os.path.isfile(exe):
        raise ScriptError("%s not found" % exe)
    return exe
