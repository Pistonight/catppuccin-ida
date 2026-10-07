"""
Writes ida.pth (untracked, so the install path stays out of the repo) in the
venv's site-packages, pointing at <ida>/python, so editors and type checkers
see the ida_* modules. The install comes from common.paths.ida_dir().
"""

import sys
import sysconfig
from pathlib import Path

from common.errors import ScriptError, run
from common.paths import ida_dir, ida_python_dir


def main():
    if len(sys.argv) > 1:
        raise ScriptError("usage: ./x setup-ida")
    location = ida_dir()
    python_dir = ida_python_dir(location)
    pth = Path(sysconfig.get_path("purelib"), "ida.pth")
    pth.write_text("%s\n" % python_dir, encoding="utf-8")
    print("wrote %s -> %s" % (pth, python_dir))


if __name__ == "__main__":
    run(main)
