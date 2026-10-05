"""Error reporting for scripts."""

import sys


class ScriptError(Exception):
    """An expected failure: printed without a traceback."""


def run(main, label):
    """Call main(); on ScriptError exit with `<label> failed: <message>`."""
    try:
        main()
    except ScriptError as e:
        sys.exit("%s failed: %s" % (label, e))
