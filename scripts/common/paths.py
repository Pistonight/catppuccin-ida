"""
Every path the scripts use: the repository, the build output, the cache,
and IDA's install and user directories.
"""

import functools
import json
import os
import re
import sys
from pathlib import Path

from common.errors import ScriptError

# --------------------------------------------------------------------------
# Repository

ROOT = Path(__file__).resolve().parents[2]
SRC = ROOT / "src"
DIST = ROOT / "dist"
# Local, untracked: tool state and generated previews
CACHE = ROOT / ".cache"

# Colour palette and role mappings (see common/config.py)
CONFIG_FILE = ROOT / "config.yaml"
# IDA icon -> codicon mapping (see scripts/build-icons.py)
ICON_CONFIG_FILE = ROOT / "config-icons-ida.yaml"
# CSS files to bundle, in order (see tools/css_bundler.py)
STYLES_LIST = SRC / "styles.txt"
# Badge overlays, from extract-modifiers (modifier_file())
MODIFIERS_DIR = SRC / "icons"
# Generated plugin modules
COLOR_GEN = SRC / "color_gen.py"
# The icons IDA's actions show (from dump-icons), and the part the plugin needs
ICON_META_FILE = SRC / "ida" / "icon_meta.yaml"
ICON_META_GEN = SRC / "ida" / "icon_meta_gen.py"
# Dock window icons by title, from config-icons-ida.yaml `windows`
WINDOW_ICONS_GEN = SRC / "ida" / "window_icons_gen.py"
# @vscode/codicons, installed with pnpm (codicon_file())
CODICONS_DIR = ROOT / "node_modules" / "@vscode" / "codicons" / "src" / "icons"
# Run inside IDA (headless) by dump-icons
IDA_DUMP_SCRIPT = ROOT / "scripts" / "ida" / "dump_icons.py"

# --------------------------------------------------------------------------
# Build output, one folder per target under dist/

# The IDA build; mirrors IDA's user directory
DIST_IDA = DIST / "catppuccin-ida"
# DIST_IDA's contents, zipped (from package)
DIST_IDA_ZIP = DIST / "catppuccin-ida.zip"
DIST_PLUGIN = DIST_IDA / "plugins" / "catppuccin.py"
DIST_THEME = DIST_IDA / "themes" / "catppuccin"
THEME_CSS = DIST_THEME / "theme.css"
ICONS_DIR = DIST_THEME / "icons"
RENDER_ICONS_PAGE = DIST / "test_icons.html"

# Installed items, relative to both DIST_IDA and the IDA user directory
INSTALL_ITEMS = [
    Path("plugins", "catppuccin.py"),
    Path("themes", "catppuccin"),
]

# --------------------------------------------------------------------------
# Cache

# The IDA install the user typed in, when ida_dir() could not find one
IDA_LOCATION_FILE = CACHE / "IDA_LOCATION.txt"
CODICON_PREVIEW = CACHE / "ida_codicon.html"
# Written by scripts/ida/dump_icons.py (its own copy of this path)
ICON_DUMP_DIR = CACHE / "ida-icon-dump"
# Original vs themed action icons (test-icons-ida)
IDA_ICON_TEST_PAGE = CACHE / "ida_icon_test.html"
DUMP_ICONS_WORK_DIR = CACHE / "dump-icons"


def rel(path):
    """`path` relative to the repository root, with forward slashes (as is if
    it is outside the repository)."""
    path = Path(path)
    return path.relative_to(ROOT).as_posix() if path.is_relative_to(ROOT) else str(path)


def file_url(path):
    """A file:/// URL for `path`, which terminals can open with a click."""
    return Path(path).resolve().as_uri()


def src_module(name):
    """src/<name>.py"""
    return SRC / (name + ".py")


def modifier_file(name):
    """src/icons/modifier-<name>.svg"""
    return MODIFIERS_DIR / ("modifier-%s.svg" % name)


def codicon_file(name):
    """The SVG of the codicon `name`; raises ScriptError if there is none."""
    path = CODICONS_DIR / (name + ".svg")
    if not CODICONS_DIR.is_dir():
        raise ScriptError("%s not found; run `pnpm install`" % rel(CODICONS_DIR))
    if not path.is_file():
        raise ScriptError("no codicon named %r (%s)" % (name, rel(path)))
    return path


def list_file_entries(path, what, hint=""):
    """(line number, entry) for the non-blank, non-# lines of a list file;
    raises ScriptError if it is missing or lists no `what`."""
    if not path.is_file():
        raise ScriptError("missing %s%s" % (rel(path), hint))
    entries = []
    with path.open(encoding="utf-8") as f:
        for lineno, line in enumerate(f, 1):
            entry = line.strip()
            if entry and not entry.startswith("#"):
                entries.append((lineno, entry))
    if not entries:
        raise ScriptError("%s lists no %s%s" % (rel(path), what, hint))
    return entries


# --------------------------------------------------------------------------
# IDA install: ida_dir() finds it, see there.

IDA_INSTALL_RE = re.compile(r"IDA Professional (\d+(?:\.\d+)*)$")
# Written by IDA into its user directory: {"Paths": {"ida-install-dir": ...}}
IDA_CONFIG_NAME = "ida-config.json"


def _configured_ida_install():
    """Paths.ida-install-dir from IDA's ida-config.json, or None."""
    try:
        config = default_ida_user_dir() / IDA_CONFIG_NAME
    except ScriptError:
        return None
    if not config.is_file():
        return None
    try:
        data = json.loads(config.read_text(encoding="utf-8"))
    except (OSError, ValueError) as e:
        raise ScriptError("%s: cannot read it: %s" % (config, e))
    paths = data.get("Paths") if isinstance(data, dict) else None
    location = paths.get("ida-install-dir") if isinstance(paths, dict) else None
    if not location:
        return None
    location = Path(location)
    try:
        ida_python_dir(location)
    except ScriptError as e:
        raise ScriptError("%s (from Paths.ida-install-dir in %s)" % (e, config))
    return location


def _is_ida_install(location):
    try:
        ida_python_dir(location)
    except ScriptError:
        return False
    return True


def _cached_ida_install():
    """The install in IDA_LOCATION_FILE, if that names a usable one."""
    if not IDA_LOCATION_FILE.is_file():
        return None
    location = Path(IDA_LOCATION_FILE.read_text(encoding="utf-8").strip())
    return location if _is_ida_install(location) else None


def _ask_ida_install():
    """Ask for the install dir until it is a usable one; records it in
    IDA_LOCATION_FILE."""
    print("Cannot automatically find IDA. Please manually enter the IDA install path (the directory containing ida.exe)")
    while True:
        try:
            answer = input("Enter IDA install path (empty to cancel): ").strip().strip('"')
        except EOFError:
            answer = ""
        if not answer:
            raise ScriptError("IDA install directory unknown")
        location = Path(answer).resolve()
        try:
            ida_python_dir(location)
        except ScriptError as e:
            print(e)
            continue
        IDA_LOCATION_FILE.parent.mkdir(parents=True, exist_ok=True)
        IDA_LOCATION_FILE.write_text("%s\n" % location, encoding="utf-8")
        print("recorded in %s" % rel(IDA_LOCATION_FILE))
        return location


def _newest_ida_install():
    """The highest-versioned IDA Professional under Program Files, or None."""
    program_files = Path(os.environ.get("SYSTEMDRIVE", "C:") + os.sep, "Program Files")
    try:
        entries = list(program_files.iterdir())
    except OSError:
        return None
    found = []
    for path in entries:
        m = IDA_INSTALL_RE.match(path.name)
        if m and path.is_dir():
            found.append((tuple(int(p) for p in m.group(1).split(".")), path))
    return max(found)[1] if found else None


def ida_python_dir(ida_dir):
    """The install's IDAPython dir; raises ScriptError if it is not usable."""
    if not (ida_dir / "ida.dll").is_file():
        raise ScriptError("%s is not a usable IDA install (missing ida.dll)" % ida_dir)
    # 9.0 keeps the modules in python/3/, later versions in python/
    for python_dir in (ida_dir / "python", ida_dir / "python" / "3"):
        if (python_dir / "ida_idaapi.py").is_file():
            return python_dir
    raise ScriptError("%s is not a usable IDA install (no IDAPython modules in python/)" % ida_dir)


@functools.cache
def ida_dir():
    """The IDA install, checked to be usable. In order:
    1. Paths.ida-install-dir in IDA's ida-config.json (IDA writes it): if
       set, always this one, and IDA_LOCATION_FILE is not used
    2. the install recorded in IDA_LOCATION_FILE, if still usable
    3. the highest-versioned IDA Professional under Program Files
    4. asks for it, and records the answer in IDA_LOCATION_FILE"""
    location = _configured_ida_install() or _cached_ida_install()
    if location is None:
        found = _newest_ida_install()
        location = found if found is not None and _is_ida_install(found) else _ask_ida_install()
    return location


def ida_exe(location):
    """The IDA GUI executable of an install."""
    exe = location / ("ida.exe" if sys.platform == "win32" else "ida")
    if not exe.is_file():
        raise ScriptError("%s not found" % exe)
    return exe


# --------------------------------------------------------------------------
# IDA user directory (where install puts dist/)

def default_ida_user_dir():
    """%APPDATA%\\Hex-Rays\\IDA Pro, or ~/.idapro."""
    if sys.platform != "win32":
        return Path.home() / ".idapro"
    appdata = os.environ.get("APPDATA")
    if not appdata:
        raise ScriptError("APPDATA is not set; pass the IDA user directory explicitly")
    return Path(appdata, "Hex-Rays", "IDA Pro")


def ida_user_dir(argv, script):
    """The IDA user directory from the command line (`./x <script> [dir]`),
    or the default: %APPDATA%\\Hex-Rays\\IDA Pro, or ~/.idapro."""
    if len(argv) > 2:
        raise ScriptError("usage: ./x %s [ida user dir]" % script)
    path = Path(argv[1]).resolve() if len(argv) == 2 else default_ida_user_dir()
    if not path.is_dir():
        raise ScriptError("%s does not exist (is IDA installed? or pass the directory)" % path)
    return path
