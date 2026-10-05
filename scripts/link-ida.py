"""
Make the local IDA install's Python modules (ida_*, idaapi, ...) visible in
the dev venv, for editors and type checking.

    uv run scripts/link-ida.py                 # auto-detect
    uv run scripts/link-ida.py "D:/IDA 9.3"    # explicit install dir

Without an argument, uses $IDADIR if set, otherwise the highest version of
%SYSTEMDRIVE%\\Program Files\\IDA Professional <version>.

Writes ida.pth into the venv's site-packages pointing at <ida>/python, so the
install path stays out of the repo.
"""

import os
import re
import sys
import sysconfig

INSTALL_RE = re.compile(r"IDA Professional (\d+(?:\.\d+)*)$")


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
    """Return (the install's IDAPython dir, None) or (None, error message)."""
    if not os.path.isfile(os.path.join(ida_dir, "ida.dll")):
        return None, "%s is not a usable IDA install (missing ida.dll)" % ida_dir
    # 9.0 keeps the modules in python/3/, later versions in python/
    for python_dir in (os.path.join(ida_dir, "python"), os.path.join(ida_dir, "python", "3")):
        if os.path.isfile(os.path.join(python_dir, "ida_idaapi.py")):
            return python_dir, None
    return None, "%s is not a usable IDA install (no IDAPython modules in python/)" % ida_dir


def main():
    ida_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("IDADIR") or find_install()
    if not ida_dir:
        sys.exit("could not find IDA under Program Files; pass the install dir:\n"
                 "    uv run scripts/link-ida.py <ida install dir>")
    python_dir, error = check_install(os.path.abspath(ida_dir))
    if python_dir is None:
        sys.exit("%s; pass a working install dir:\n" % error +
                 "    uv run scripts/link-ida.py <ida install dir>")
    pth = os.path.join(sysconfig.get_path("purelib"), "ida.pth")
    with open(pth, "w", encoding="utf-8") as f:
        f.write(python_dir + "\n")
    print("wrote %s -> %s" % (pth, python_dir))


if __name__ == "__main__":
    main()
