"""
Check the CSS sources against the config file.

    uv run scripts/check-css.py

For the CSS files listed in src/styles.txt:
- every `${...}` reference is a role (ctp-r-*) defined in the config file,
  or an @def declared in the CSS itself; colours (ctp-c-*) and definitions
  (ctp-d-*) are only for the roles to use
- every role is used exactly once, and every role is used
- no comment contains a dollar-brace sequence (IDA expands those even there)
"""

import re

from common.config import colors, definitions, load_config, roles
from common.errors import ScriptError, run
from common.paths import CONFIG_FILE, rel
from common.styles import style_list, style_path

REF_RE = re.compile(r"\$\{([^}]*)\}")
DEF_RE = re.compile(r"^\s*@def\s+(\S+)", re.M)
COMMENT_RE = re.compile(r"/\*.*?\*/", re.S)
ROLE_PREFIX = "ctp-r-"


def main():
    config = load_config()
    color_values = colors(config)
    role_names = {ROLE_PREFIX + name for name, _ in
                  roles(config, color_values, definitions(config, color_values))}

    sources = {}
    for path in style_list():
        with open(style_path(path), encoding="utf-8") as f:
            sources[path] = f.read()
    local_defs = {name for text in sources.values() for name in DEF_RE.findall(text)}

    errors = []
    uses = {}   # role -> ["src/file:line", ...]
    for path, text in sources.items():
        for m in COMMENT_RE.finditer(text):
            if "${" in m.group(0):
                line = text.count("\n", 0, m.start()) + 1
                errors.append("src/%s:%d: comment contains a dollar-brace sequence" % (path, line))
        code = COMMENT_RE.sub(lambda m: "\n" * m.group(0).count("\n"), text)
        for lineno, line in enumerate(code.split("\n"), 1):
            for m in REF_RE.finditer(line):
                name, where = m.group(1), "src/%s:%d" % (path, lineno)
                if name in role_names:
                    uses.setdefault(name, []).append(where)
                elif name in local_defs:
                    pass
                elif name.startswith(ROLE_PREFIX):
                    errors.append("%s: %s is not a role in %s" % (where, name, rel(CONFIG_FILE)))
                else:
                    errors.append("%s: %s is not a role (CSS may only use %s* roles)"
                                  % (where, name, ROLE_PREFIX))

    for name, places in sorted(uses.items()):
        if len(places) > 1:
            errors.append("%s is used %d times (%s); each role is for one place"
                          % (name, len(places), ", ".join(places)))
    unused = sorted(role_names - set(uses))
    for name in unused:
        errors.append("%s is defined in %s but not used" % (name, rel(CONFIG_FILE)))

    for e in errors:
        print(e)
    if errors:
        raise ScriptError("%d problem(s)" % len(errors))
    print("ok: %d roles, each used once" % len(role_names))


if __name__ == "__main__":
    run(main, "check-css")
