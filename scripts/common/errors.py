"""Error reporting for scripts."""

import sys
from pathlib import Path


class ScriptError(Exception):
    """An expected failure: printed without a traceback."""


def run(main):
    """Call main(); on ScriptError exit with `<script> failed: <message>`,
    <script> being the name of the file main() is defined in."""
    script = Path(sys.modules[main.__module__].__file__ or "script").stem
    try:
        main()
    except ScriptError as e:
        sys.exit("%s failed: %s" % (script, e))
