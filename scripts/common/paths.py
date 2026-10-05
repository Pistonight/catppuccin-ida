"""Repository paths."""

import os
import pathlib

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")
# The theme folder inside dist (theme.css, icons/)
DIST_THEME = os.path.join(DIST, "themes", "catppuccin")
# Local, untracked: tool state and generated previews
CACHE = os.path.join(ROOT, ".cache")

# Colour palette and role mappings (see common/config.py)
CONFIG_FILE = os.path.join(ROOT, "config.yaml")
# IDA icon -> codicon mapping (see scripts/build-icons.py)
ICON_CONFIG_FILE = os.path.join(ROOT, "config-icons-ida.yaml")


def rel(path):
    """`path` relative to the repository root, with forward slashes."""
    return os.path.relpath(path, ROOT).replace(os.sep, "/")


def file_url(path):
    """A file:/// URL for `path`, which terminals can open with a click."""
    return pathlib.Path(path).resolve().as_uri()
