"""Bundle the CSS files listed in a .txt file into one style sheet.

The list has one CSS path per line, relative to the folder containing the
list; blank lines and lines starting with # are ignored. The files are
concatenated in that order, each under a banner comment naming it.
"""

from typing import NamedTuple

from common.errors import ScriptError
from common.paths import list_file_entries, rel

BANNER_RULE = "-" * 66


class CssBundle(NamedTuple):
    source: str     # the bundled CSS (no trailing newline)
    files: list     # paths of the bundled files, in order


def css_banner(title):
    """A banner comment heading a section of a bundled style sheet."""
    return "/* %s *\n * %s\n * %s */" % (BANNER_RULE, title, BANNER_RULE)


def css_file_list(list_path):
    """The CSS files listed in `list_path`, in order (checked to exist and to
    be listed once)."""
    folder = list_path.parent
    files = []
    for lineno, entry in list_file_entries(list_path, "CSS files"):
        path = (folder / entry).resolve()
        where = "%s:%d" % (rel(list_path), lineno)
        if path in files:
            raise ScriptError("%s: %s is listed twice" % (where, entry))
        if not path.is_file():
            raise ScriptError("%s: %s does not exist" % (where, rel(path)))
        files.append(path)
    return files


def bundle_css_files(list_path):
    """The CSS files listed in `list_path`, concatenated in order, each under
    a css_banner() with its path."""
    files = css_file_list(list_path)
    parts = []
    for path in files:
        css = path.read_text(encoding="utf-8").strip("\n")
        parts.append("%s\n\n%s" % (css_banner(rel(path)), css))
    return CssBundle("\n\n".join(parts), files)
