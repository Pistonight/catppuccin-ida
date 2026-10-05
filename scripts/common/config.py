"""The colour config file (common.paths.CONFIG_FILE).

Generated CSS variables are ctp-<kind>-<name>:
  ctp-c-<name>  colours: `palette` entries and `tints`
  ctp-d-<name>  definitions: aliases of colours
  ctp-r-<name>  roles: nested; namespaces joined with `--`

Within the file, values refer to other entries without the ctp- prefix
(`c-green`, `d-keyword`). Tints and definitions refer to palette colours
(tints: palette only; definitions: any colour); roles refer to colours or
definitions, never to other roles.
"""

import os
import re

import yaml

from common.errors import ScriptError
from common.paths import CONFIG_FILE, rel

# Which build consumes each top-level role namespace; any namespace not listed
# here is for the CSS (ctp-r-* in the theme).
CSS = "css"
PYTHON = "python"   # the plugin, via src/color_gen.py (scripts/build-css.py)
ICONS = "icons"     # generated SVGs (scripts/build-icons.py)
ROLE_TARGETS = {
    "titlebar": PYTHON,
    "arrows": ICONS,
    "indicators": ICONS,
}

NAME_RE = re.compile(r"[a-z0-9]+(-[a-z0-9]+)*")
HEX_RE = re.compile(r"#[0-9a-fA-F]{6}")
DEFAULT_TINT_BASE = "c-base"


def _fail(msg):
    raise ScriptError("%s: %s" % (rel(CONFIG_FILE), msg))


def _check_name(name, where):
    if not isinstance(name, str) or not NAME_RE.fullmatch(name):
        _fail("%s: invalid name %r (lowercase words joined by single dashes)" % (where, name))


def load_config():
    """The parsed config file."""
    if not os.path.isfile(CONFIG_FILE):
        raise ScriptError("missing %s" % rel(CONFIG_FILE))
    with open(CONFIG_FILE, encoding="utf-8") as f:
        data = yaml.safe_load(f)
    if not isinstance(data, dict):
        _fail("expected a mapping at the top level")
    for section in ("palette", "tints", "definitions", "roles"):
        if not isinstance(data.get(section), dict):
            _fail("missing section `%s`" % section)
    return data


def _rgb(hex_color):
    return tuple(int(hex_color[i:i + 2], 16) for i in (1, 3, 5))


def _format_alpha(alpha):
    text = "%.2f" % alpha
    return text if float(text) == alpha else repr(alpha)


def colors(config):
    """ctp-c-* values by name (without prefix), as CSS colour strings."""
    out = {}
    for name, value in config["palette"].items():
        _check_name(name, "palette")
        if not isinstance(value, str) or not HEX_RE.fullmatch(value):
            _fail("palette.%s: expected a '#rrggbb' hex colour, got %r" % (name, value))
        out[name] = value.lower()

    def palette_rgb(ref, where):
        if not isinstance(ref, str) or not ref.startswith("c-") or ref[2:] not in config["palette"]:
            _fail("%s: %r is not a palette colour (c-<name>)" % (where, ref))
        return _rgb(out[ref[2:]])

    for name, tint in config["tints"].items():
        _check_name(name, "tints")
        where = "tints.%s" % name
        if name in out:
            _fail("%s: name already used by the palette" % where)
        if not isinstance(tint, dict) or "color" not in tint:
            _fail("%s: expected { color: c-<name>, amount: x } or { color: ..., alpha: x }" % where)
        color = palette_rgb(tint["color"], where + ".color")
        if ("amount" in tint) == ("alpha" in tint):
            _fail("%s: give exactly one of `amount` (blend) or `alpha` (translucent)" % where)
        if "alpha" in tint:
            if "onto" in tint:
                _fail("%s: `onto` only applies to `amount` tints" % where)
            out[name] = "rgba(%d, %d, %d, %s)" % (color + (_format_alpha(tint["alpha"]),))
        else:
            base = palette_rgb(tint.get("onto", DEFAULT_TINT_BASE), where + ".onto")
            amount = tint["amount"]
            mixed = tuple(round(b + amount * (c - b)) for c, b in zip(color, base))
            out[name] = "#%02x%02x%02x" % mixed
    return out


def _check_ref(ref, allowed, known, where):
    """`ref` must be <kind>-<name> with kind in `allowed` and name in known[kind]."""
    if isinstance(ref, str):
        kind, _, name = ref.partition("-")
        if kind in allowed and name in known[kind]:
            return
    _fail("%s: %r must refer to %s" % (where, ref, " or ".join("%s-<name>" % k for k in allowed)))


def definitions(config, color_values):
    """ctp-d-* by name: the c- reference each one points at."""
    out = {}
    for name, ref in config["definitions"].items():
        _check_name(name, "definitions")
        _check_ref(ref, ("c",), {"c": color_values}, "definitions.%s" % name)
        out[name] = ref
    return out


def roles(config, color_values, definition_values, target=CSS):
    """Roles for one build target (see ROLE_TARGETS), in file order:
    [(name, reference)], name joined with `--`."""
    known = {"c": color_values, "d": definition_values}
    out = []

    def walk(node, path):
        for key, value in node.items():
            _check_name(key, "roles." + ".".join(path) if path else "roles")
            here = path + [key]
            if isinstance(value, dict):
                walk(value, here)
            else:
                _check_ref(value, ("c", "d"), known, "roles." + ".".join(here))
                out.append(("--".join(here), value))

    for key, value in config["roles"].items():
        if ROLE_TARGETS.get(key, CSS) != target:
            continue
        if not isinstance(value, dict):
            _fail("roles.%s: expected a namespace" % key)
        walk({key: value}, [])
    return out


def resolve(ref, color_values, definition_values):
    """The final colour value of a c- or d- reference."""
    if ref.startswith("d-"):
        ref = definition_values[ref[2:]]
    return color_values[ref[2:]]
