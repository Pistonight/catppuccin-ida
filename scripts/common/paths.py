"""Repository paths."""

import os

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
SRC = os.path.join(ROOT, "src")
DIST = os.path.join(ROOT, "dist")

# Colour palette and role mappings (see common/const.py)
CONST_FILE = os.path.join(ROOT, "const.yaml")


def rel(path):
    """`path` relative to the repository root, with forward slashes."""
    return os.path.relpath(path, ROOT).replace(os.sep, "/")
