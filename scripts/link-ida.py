"""
Point the dev venv at the local IDA install.

    uv run scripts/link-ida.py                 # auto-detect
    uv run scripts/link-ida.py "D:/IDA 9.3"    # explicit install dir

Without an argument, uses $IDADIR if set, otherwise the highest version of
%SYSTEMDRIVE%\\Program Files\\IDA Professional <version>.

Writes (both untracked, so the install path stays out of the repo):
- ida.pth in the venv's site-packages, pointing at <ida>/python, so editors
  and type checkers see the ida_* modules
- .cache/IDA_LOCATION.txt, the install dir, for scripts that run IDA
"""

import os
import sys
import sysconfig

from common.errors import ScriptError, run
from common.ida import check_install, find_install, location_file

USAGE = "    uv run scripts/link-ida.py <ida install dir>"


def main():
    ida_dir = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("IDADIR") or find_install()
    if not ida_dir:
        raise ScriptError("could not find IDA under Program Files; pass the install dir:\n" + USAGE)
    ida_dir = os.path.abspath(ida_dir)
    try:
        python_dir = check_install(ida_dir)
    except ScriptError as e:
        raise ScriptError("%s; pass a working install dir:\n%s" % (e, USAGE))

    pth = os.path.join(sysconfig.get_path("purelib"), "ida.pth")
    with open(pth, "w", encoding="utf-8") as f:
        f.write(python_dir + "\n")
    print("wrote %s -> %s" % (pth, python_dir))

    location = location_file()
    os.makedirs(os.path.dirname(location), exist_ok=True)
    with open(location, "w", encoding="utf-8") as f:
        f.write(ida_dir + "\n")
    print("wrote %s -> %s" % (location, ida_dir))


if __name__ == "__main__":
    run(main, "link-ida")
