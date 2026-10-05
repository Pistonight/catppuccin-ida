"""
Build the theme's icons into dist.

    uv run scripts/build-icons.py    -> dist/themes/catppuccin/icons/
                                        .cache/ida_codicon.html

Colours come from the config file (common.paths.CONFIG_FILE).

- Arrows: arrow-{up,down,left,right}[-<state>].svg for every state in
  roles.arrows (`normal` has no suffix), used by src/css/icons_arrow.css
  and the plugin's nav band buttons.
- Check box / radio marks: checkbox-checked, checkbox-indeterminate and
  radio-checked.svg, coloured by roles.indicators, used by
  src/css/icons_indicator.css.
- IDA's toolbar/menu icons: menu/<Name>.svg for every icon in the icon config
  (common.paths.ICON_CONFIG_FILE); build-css points IDA at them. Each is a
  codicon in a colour, optionally with a modifier badge
  (src/icons/modifier-<name>.svg) layered on its bottom-right corner, with the
  codicon cut away around the badge. .cache/ida_codicon.html shows them all.
- Swapped icons: swapped/<resource path>.svg for the icon config's `swapped`
  section, icons IDA loads straight from its resources (e.g. Local Types
  rows); the plugin swaps them at runtime.
- Plugin icons: plugin/<name>.svg for the icon config's `plugin` section,
  icons IDA has no name for (e.g. the dock header close button).
- src/icons_gen.py: for the plugin, the dock window icons by title (the icon
  config's `windows` section) and the plugin icons' paths.
"""

import os
import re
import shutil

import yaml

from common.codicons import BADGE_CX, BADGE_CY, BADGE_GAP_R, codicon_path, icon_body, svg_body
from common.config import HEX_RE, ICONS, colors, definitions, load_config, resolve, roles
from common.errors import ScriptError, run
from common.ida_icons import ICON_LIST, ida_icon_names
from common.paths import CACHE, CONFIG_FILE, DIST_THEME, ICON_CONFIG_FILE, SRC, file_url, rel
from common.render import write_page

ICONS_DIR = os.path.join(DIST_THEME, "icons")
MENU_DIR = os.path.join(ICONS_DIR, "menu")
# Icons the plugin swaps at runtime, at icons/swapped/<resource path>.svg
SWAPPED_DIR = os.path.join(ICONS_DIR, "swapped")
SWAPPED_SECTION = "swapped"
SWAPPED_KEY_RE = re.compile(r"[\w-]+(/[\w-]+)*")
PLUGIN_DIR = os.path.join(ICONS_DIR, "plugin")
PLUGIN_SECTION = "plugin"
PLUGIN_PREFIX = "plugin/"    # windows: values naming a plugin icon
WINDOWS_SECTION = "windows"
WILDCARD = "*"
PY_OUT = os.path.join(SRC, "icons_gen.py")
MODIFIERS_DIR = os.path.join(SRC, "icons")
PREVIEW = os.path.join(CACHE, "ida_codicon.html")

# 10x10 triangles, by direction
ARROWS = {
    "up": "1,7 9,7 5,2",
    "down": "1,3 9,3 5,8",
    "left": "7,1 7,9 2,5",
    "right": "3,1 3,9 8,5",
}
ARROW_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10" viewBox="0 0 10 10">'
             '<polygon points="%s" fill="%s"/></svg>\n')
ARROW_NORMAL_STATE = "normal"

# Check box / radio button marks, drawn into the 12px indicators: file name ->
# (role in roles.indicators, shape). Strokes are thicker than codicons' so
# they stay legible that small.
INDICATORS = {
    "checkbox-checked": ("check", '<path d="M3.5 8.5L6.5 11.5L12.5 4.5" fill="none" stroke="%s" '
                                  'stroke-width="2.2" stroke-linecap="round" stroke-linejoin="round"/>'),
    "checkbox-indeterminate": ("check", '<path d="M4 8H12" fill="none" stroke="%s" '
                                        'stroke-width="2.2" stroke-linecap="round"/>'),
    "radio-checked": ("radio", '<circle cx="8" cy="8" r="3.5" fill="%s"/>'),
}
INDICATOR_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
                 '%s</svg>\n')

ICON_SVG = ('<svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
            '%s</svg>\n')
BADGE_GAP_MASK = (
    '<defs><mask id="badge-gap" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">'
    '<rect width="16" height="16" fill="#fff"/>'
    '<circle cx="%g" cy="%g" r="%g" fill="#000"/></mask></defs>' % (BADGE_CX, BADGE_CY, BADGE_GAP_R))


def _resolved(ref, color_values, definition_values, where, config_file):
    """The opaque colour of a c-/d- reference from a config file."""
    kind, _, name = ref.partition("-") if isinstance(ref, str) else ("", "", "")
    known = color_values if kind == "c" else definition_values if kind == "d" else {}
    if name not in known:
        raise ScriptError("%s: %s: %r must refer to c-<name> or d-<name> in %s"
                          % (rel(config_file), where, ref, rel(CONFIG_FILE)))
    value = resolve(ref, color_values, definition_values)
    if not HEX_RE.fullmatch(value):
        raise ScriptError("%s: %s resolves to %s; icons need an opaque #rrggbb colour"
                          % (rel(config_file), where, value))
    return value


def icon_colors(config, color_values, definition_values):
    """{role name: resolved colour} for the icon roles, e.g. {"arrows--hover": "#cdd6f4"}."""
    out = {}
    for name, ref in roles(config, color_values, definition_values, ICONS):
        where = "roles." + name.replace("--", ".")
        out[name] = _resolved(ref, color_values, definition_values, where, CONFIG_FILE)
    return out


def build_arrow_icons(icon_roles):
    prefix = "arrows--"
    states = {name[len(prefix):]: value for name, value in icon_roles.items() if name.startswith(prefix)}
    if ARROW_NORMAL_STATE not in states:
        raise ScriptError("%s: missing roles.arrows.%s" % (rel(CONFIG_FILE), ARROW_NORMAL_STATE))
    os.makedirs(ICONS_DIR, exist_ok=True)
    written = 0
    for state, color in states.items():
        suffix = "" if state == ARROW_NORMAL_STATE else "-" + state
        for direction, points in ARROWS.items():
            path = os.path.join(ICONS_DIR, "arrow-%s%s.svg" % (direction, suffix))
            with open(path, "w", encoding="utf-8", newline="\n") as f:
                f.write(ARROW_SVG % (points, color))
            written += 1
    print("built %d arrow icons (%s) in %s" % (written, ", ".join(states), rel(ICONS_DIR)))


def build_indicator_icons(icon_roles):
    os.makedirs(ICONS_DIR, exist_ok=True)
    for name, (role, shape) in INDICATORS.items():
        key = "indicators--" + role
        if key not in icon_roles:
            raise ScriptError("%s: missing roles.indicators.%s" % (rel(CONFIG_FILE), role))
        with open(os.path.join(ICONS_DIR, name + ".svg"), "w", encoding="utf-8", newline="\n") as f:
            f.write(INDICATOR_SVG % (shape % icon_roles[key]))
    print("built %d indicator icons in %s" % (len(INDICATORS), rel(ICONS_DIR)))


def _colored(body, color):
    """An icon's markup in one colour. Icons fill with currentColor, set on
    their (dropped) <svg> element and sometimes on the shapes themselves."""
    return '<g fill="%s">%s</g>' % (color, body.replace("currentColor", color))


def _compose(name, entry, modifiers, color_values, definition_values):
    """An icon config entry as SVG markup, and a label for the preview."""
    where = "%s: %s" % (rel(ICON_CONFIG_FILE), name)
    base = entry.get("base") if isinstance(entry, dict) else None
    if not (isinstance(base, list) and len(base) == 2):
        raise ScriptError("%s: expected `base: [<codicon>, <colour>]`" % where)
    codicon, ref = base
    color = _resolved(ref, color_values, definition_values, name + ".base", ICON_CONFIG_FILE)
    body = _colored(icon_body(codicon_path(codicon)), color)
    modifier = entry.get("modifier")
    if modifier is None:
        layers = body
    elif modifier in modifiers:
        layers = '%s<g mask="url(#badge-gap)">%s</g>%s' % (BADGE_GAP_MASK, body, modifiers[modifier])
    else:
        raise ScriptError("%s: unknown modifier %r (defined: %s)"
                          % (where, modifier, ", ".join(modifiers)))
    label = "%s (%s%s)" % (name, codicon, " + " + modifier if modifier else "")
    return ICON_SVG % layers, label


def _write_icons(entries, out_dir, modifiers, color_values, definition_values):
    """Build {relative name: entry} into out_dir/<name>.svg; returns preview items."""
    if os.path.isdir(out_dir):
        shutil.rmtree(out_dir)
    preview = []
    for name, entry in entries.items():
        svg, label = _compose(name, entry, modifiers, color_values, definition_values)
        path = os.path.join(out_dir, *name.split("/")) + ".svg"
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            f.write(svg)
        preview.append((label, path))
    return preview


def build_ida_icons(color_values, definition_values):
    with open(ICON_CONFIG_FILE, encoding="utf-8") as f:
        icon_config = yaml.safe_load(f)
    if not isinstance(icon_config, dict) or not isinstance(icon_config.get("modifiers"), dict):
        raise ScriptError("%s: expected a `modifiers` section and one entry per icon"
                          % rel(ICON_CONFIG_FILE))

    modifiers = {}
    for name, ref in icon_config.pop("modifiers").items():
        path = os.path.join(MODIFIERS_DIR, "modifier-%s.svg" % name)
        if not os.path.isfile(path):
            raise ScriptError("%s: modifiers.%s: %s does not exist (see scripts/extract-modifiers.py)"
                              % (rel(ICON_CONFIG_FILE), name, rel(path)))
        color = _resolved(ref, color_values, definition_values, "modifiers." + name, ICON_CONFIG_FILE)
        modifiers[name] = _colored(svg_body(path), color)

    swapped = _section(icon_config, SWAPPED_SECTION, "resource paths to icons")
    plugin_icons = _section(icon_config, PLUGIN_SECTION, "names to icons")
    windows = _section(icon_config, WINDOWS_SECTION, "window titles to icon names")
    bad = [k for k in swapped if not SWAPPED_KEY_RE.fullmatch(str(k))]
    if bad:
        raise ScriptError("%s: %s keys must be resource paths under :/ without .svg, e.g. "
                          "IDAG/resources/widgets/struct: %s"
                          % (rel(ICON_CONFIG_FILE), SWAPPED_SECTION, ", ".join(map(str, bad))))

    themable = ida_icon_names()
    unknown = sorted(set(icon_config) - set(themable))
    if unknown:
        raise ScriptError("%s: not in %s: %s"
                          % (rel(ICON_CONFIG_FILE), rel(ICON_LIST), ", ".join(unknown)))

    preview = _write_icons(icon_config, MENU_DIR, modifiers, color_values, definition_values)
    missing = [n for n in themable if n not in icon_config]
    print("built %d IDA icons in %s" % (len(preview), rel(MENU_DIR)))
    if missing:
        print("warning: no icon configured for %d: %s" % (len(missing), ", ".join(missing)))

    swapped_preview = _write_icons(swapped, SWAPPED_DIR, modifiers, color_values, definition_values)
    print("built %d swapped icons in %s" % (len(swapped_preview), rel(SWAPPED_DIR)))

    bad = [k for k in plugin_icons if not re.fullmatch(r"[a-z0-9]+(-[a-z0-9]+)*", str(k))]
    if bad:
        raise ScriptError("%s: %s keys must be lower-case-dashed names: %s"
                          % (rel(ICON_CONFIG_FILE), PLUGIN_SECTION, ", ".join(map(str, bad))))
    plugin_preview = _write_icons(plugin_icons, PLUGIN_DIR, modifiers, color_values, definition_values)
    print("built %d plugin icons in %s" % (len(plugin_preview), rel(PLUGIN_DIR)))

    write_page(preview + swapped_preview + plugin_preview, "IDA icons from codicons", PREVIEW)
    print("rendered them to %s" % file_url(PREVIEW))

    with open(PY_OUT, "w", encoding="utf-8", newline="\n") as f:
        f.write(generate_python(windows, plugin_icons, icon_config))
    print("wrote %s" % rel(PY_OUT))


def _section(icon_config, name, what):
    section = icon_config.pop(name, None) or {}
    if not isinstance(section, dict):
        raise ScriptError("%s: `%s` must map %s" % (rel(ICON_CONFIG_FILE), name, what))
    return section


def _icon_path(*parts):
    """A built icon's path under the theme's icons/ folder, as the plugin uses it."""
    return os.path.relpath(os.path.join(*parts), ICONS_DIR).replace(os.sep, "/") + ".svg"


def generate_python(windows, plugin_icons, icon_config):
    """src/icons_gen.py: dock window icons by title, and the plugin icons."""
    lines = ['"""Icons used by the plugin, as paths under the theme\'s icons/ folder.',
             "",
             "Generated by scripts/build-icons.py from %s -- do not edit." % rel(ICON_CONFIG_FILE),
             '"""', "",
             "# (window title, or its start if is_prefix; icon)",
             "WINDOW_ICONS = ["]
    for title, name in windows.items():
        where = "%s: %s.%r" % (rel(ICON_CONFIG_FILE), WINDOWS_SECTION, title)
        title = str(title)
        name = str(name)
        if name.startswith(PLUGIN_PREFIX) and name[len(PLUGIN_PREFIX):] in plugin_icons:
            path = _icon_path(PLUGIN_DIR, name[len(PLUGIN_PREFIX):])
        elif name in icon_config:
            path = _icon_path(MENU_DIR, name)
        else:
            raise ScriptError("%s: %r is neither an IDA icon defined above nor %s<name> from `%s`"
                              % (where, name, PLUGIN_PREFIX, PLUGIN_SECTION))
        is_prefix = title.endswith(WILDCARD)
        title = title[:-len(WILDCARD)] if is_prefix else title
        if not title or WILDCARD in title:
            raise ScriptError("%s: %s is only allowed at the end of a title" % (where, WILDCARD))
        lines.append("    (%r, %r, %r)," % (title, is_prefix, path))
    lines.append("]")
    for name in plugin_icons:
        lines.append("%s_ICON = %r" % (str(name).replace("-", "_").upper(), _icon_path(PLUGIN_DIR, name)))
    return "\n".join(lines) + "\n"


def main():
    config = load_config()
    color_values = colors(config)
    definition_values = definitions(config, color_values)
    icon_roles = icon_colors(config, color_values, definition_values)
    build_arrow_icons(icon_roles)
    build_indicator_icons(icon_roles)
    build_ida_icons(color_values, definition_values)


if __name__ == "__main__":
    run(main, "build-icons")
