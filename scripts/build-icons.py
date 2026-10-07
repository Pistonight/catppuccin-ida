"""
Build the theme's icons into dist.

    uv run scripts/build-icons.py    -> dist/catppuccin-ida/themes/catppuccin/icons/
                                        .cache/ida_codicon.html

Colours come from the config file (common.paths.CONFIG_FILE).

- Arrows: arrow-{up,down,left,right}[-<state>].svg for every state in
  roles.arrows (`normal` has no suffix), used by src/css/icons_arrow.css
  and the plugin's nav band buttons.
- Check box / radio / menu marks: checkbox-checked, checkbox-indeterminate,
  radio-checked, menu-checked and menu-selected.svg, coloured by
  roles.indicators, used by src/css/icons_indicator.css.
- IDA's icons: themes/catppuccin/<path> for every entry of the icon config's
  `icons` section (common.paths.ICON_CONFIG_FILE), keyed by the path in
  src/ida/icon_meta.yaml (from dump-icons); the plugin sets them on IDA's
  actions. Each is a codicon in a colour, optionally with a modifier badge
  (src/icons/modifier-<name>.svg) layered on its bottom-right corner, with
  the codicon cut away around the badge. .cache/ida_codicon.html shows them
  all. A path missing from the metadata fails the build; metadata icons
  with no entry only warn (IDA's icon stays). Other top-level entries of the
  icon config (the 9.3 layout: names, `swapped`, `windows`, `plugin`) are
  ignored.
- src/ida/icon_meta_gen.py: for the plugin, the icons IDA loads without a
  name, from src/ida/icon_meta.yaml (the `map_by_action` entries, written
  by dump-icons): their path and the actions to match.
"""


import yaml

from common.codicons import BADGE_CX, BADGE_CY, BADGE_GAP_R, BADGE_R, icon_body, svg_body
from common.config import HEX_RE, ICONS, colors, definitions, load_config, resolve, roles
from common.errors import ScriptError, run
from common.icon_meta import load_icon_meta
from common.paths import (CODICON_PREVIEW, CONFIG_FILE, DIST_THEME, ICON_CONFIG_FILE, ICON_META_FILE,
                          ICON_META_GEN, ICONS_DIR, WINDOW_ICONS_GEN, codicon_file, file_url, modifier_file, rel)
from common.render import write_page

ICONS_SECTION = "icons"
EXTRA_PREFIX = "extra/"      # icons IDA has no resource for (plugin, CSS)
WINDOWS_SECTION = "windows"
WILDCARD = "*"               # windows: a trailing * matches any suffix
UNMAPPED_SHOWN = 10          # unmapped icons listed in the warning

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
    # Checked menu entries: thinner, unboxed, in the menu's text colour
    "menu-checked": ("menu", '<path d="M3.5 8.5L6.5 11.5L12.5 4.5" fill="none" stroke="%s" '
                             'stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round"/>'),
    "menu-selected": ("menu", '<circle cx="8" cy="8" r="3" fill="%s"/>'),
}
INDICATOR_SVG = ('<svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 16 16">'
                 '%s</svg>\n')

ICON_SVG = ('<svg width="16" height="16" viewBox="0 0 16 16" xmlns="http://www.w3.org/2000/svg">'
            '%s</svg>\n')
# Modifier badges are drawn at BADGE_SCALE of the codicon badge's size,
# shrunk towards the icon's bottom-right corner (the badge circle touches
# both edges, so it stays in the corner); the gap cut around them keeps its
# width.
BADGE_SCALE = 0.8
BADGE_CORNER = 16
BADGE_TRANSFORM = "translate(%g %g) scale(%g) translate(%g %g)" % (
    BADGE_CORNER, BADGE_CORNER, BADGE_SCALE, -BADGE_CORNER, -BADGE_CORNER)
BADGE_GAP_MASK = (
    '<defs><mask id="badge-gap" maskUnits="userSpaceOnUse" x="0" y="0" width="16" height="16">'
    '<rect width="16" height="16" fill="#fff"/>'
    '<circle cx="%g" cy="%g" r="%g" fill="#000"/></mask></defs>' % (
        BADGE_CORNER - (BADGE_CORNER - BADGE_CX) * BADGE_SCALE,
        BADGE_CORNER - (BADGE_CORNER - BADGE_CY) * BADGE_SCALE,
        BADGE_R * BADGE_SCALE + (BADGE_GAP_R - BADGE_R)))


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
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    written = 0
    for state, color in states.items():
        suffix = "" if state == ARROW_NORMAL_STATE else "-" + state
        for direction, points in ARROWS.items():
            path = ICONS_DIR / ("arrow-%s%s.svg" % (direction, suffix))
            path.write_text(ARROW_SVG % (points, color), encoding="utf-8", newline="\n")
            written += 1
    print("built %d arrow icons (%s) in %s" % (written, ", ".join(states), rel(ICONS_DIR)))


def build_indicator_icons(icon_roles):
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    for name, (role, shape) in INDICATORS.items():
        key = "indicators--" + role
        if key not in icon_roles:
            raise ScriptError("%s: missing roles.indicators.%s" % (rel(CONFIG_FILE), role))
        (ICONS_DIR / (name + ".svg")).write_text(INDICATOR_SVG % (shape % icon_roles[key]),
                                                 encoding="utf-8", newline="\n")
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
    body = _colored(icon_body(codicon_file(codicon)), color)
    modifier = entry.get("modifier")
    if modifier is None:
        layers = body
    elif modifier in modifiers:
        layers = '%s<g mask="url(#badge-gap)">%s</g><g transform="%s">%s</g>' % (
            BADGE_GAP_MASK, body, BADGE_TRANSFORM, modifiers[modifier])
    else:
        raise ScriptError("%s: unknown modifier %r (defined: %s)"
                          % (where, modifier, ", ".join(modifiers)))
    label = "%s (%s%s)" % (name, codicon, " + " + modifier if modifier else "")
    return ICON_SVG % layers, label


def build_ida_icons(color_values, definition_values):
    """themes/catppuccin/<path> for every icon in the icon config's `icons`
    section (keyed by the path in src/ida/icon_meta.yaml, or extra/<name>.svg
    for icons IDA has no resource for); returns the icon config."""
    with ICON_CONFIG_FILE.open(encoding="utf-8") as f:
        icon_config = yaml.safe_load(f)
    if not isinstance(icon_config, dict) or not isinstance(icon_config.get("modifiers"), dict) \
            or not isinstance(icon_config.get(ICONS_SECTION), dict):
        raise ScriptError("%s: expected `modifiers` and `%s` sections" % (rel(ICON_CONFIG_FILE), ICONS_SECTION))

    modifiers = {}
    for name, ref in icon_config["modifiers"].items():
        path = modifier_file(name)
        if not path.is_file():
            raise ScriptError("%s: modifiers.%s: %s does not exist (see scripts/extract-modifiers.py)"
                              % (rel(ICON_CONFIG_FILE), name, rel(path)))
        color = _resolved(ref, color_values, definition_values, "modifiers." + name, ICON_CONFIG_FILE)
        modifiers[name] = _colored(svg_body(path), color)

    icons = {str(path): entry for path, entry in icon_config[ICONS_SECTION].items()}
    meta = [icon.path for icon in load_icon_meta()]
    unknown = sorted(path for path in set(icons) - set(meta) if not path.startswith(EXTRA_PREFIX))
    if unknown:
        raise ScriptError("%s: %s: not in %s (nor under %s): %s"
                          % (rel(ICON_CONFIG_FILE), ICONS_SECTION, rel(ICON_META_FILE), EXTRA_PREFIX,
                             ", ".join(unknown)))

    preview = []
    for path, entry in sorted(icons.items()):
        svg, label = _compose(path, entry, modifiers, color_values, definition_values)
        target = DIST_THEME / path
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(svg, encoding="utf-8", newline="\n")
        preview.append((label, target))
    print("built %d IDA icons in %s" % (len(preview), rel(DIST_THEME)))

    unmapped = [path for path in meta if path not in icons]
    if unmapped:
        shown = ", ".join(unmapped[:UNMAPPED_SHOWN]) + (", ..." if len(unmapped) > UNMAPPED_SHOWN else "")
        print("warning: %d of %d icons in %s have no entry in %s %s (IDA's stay): %s"
              % (len(unmapped), len(meta), rel(ICON_META_FILE), rel(ICON_CONFIG_FILE), ICONS_SECTION, shown))

    write_page(preview, "IDA icons from codicons", CODICON_PREVIEW)
    print("rendered them to %s" % file_url(CODICON_PREVIEW))
    return icon_config


def build_window_icons(icon_config):
    """src/ida/window_icons_gen.py from the icon config's `windows` section:
    dock window title (a trailing * matches any suffix) -> icon path, which
    must be in `icons`."""
    windows = icon_config.get(WINDOWS_SECTION) or {}
    if not isinstance(windows, dict):
        raise ScriptError("%s: `%s` must map window titles to icon paths" % (rel(ICON_CONFIG_FILE), WINDOWS_SECTION))
    icons = icon_config[ICONS_SECTION]
    rules = []
    for title, path in windows.items():
        where = "%s: %s.%r" % (rel(ICON_CONFIG_FILE), WINDOWS_SECTION, title)
        title, path = str(title), str(path)
        if path not in icons:
            raise ScriptError("%s: %r is not an icon path in `%s`" % (where, path, ICONS_SECTION))
        is_prefix = title.endswith(WILDCARD)
        title = title[:-len(WILDCARD)] if is_prefix else title
        if not title or WILDCARD in title:
            raise ScriptError("%s: %s is only allowed at the end of a title" % (where, WILDCARD))
        rules.append((title, is_prefix, path))
    lines = ['"""Dock window icons by window title.',
             "",
             "Generated by scripts/build-icons.py from %s -- do not edit." % rel(ICON_CONFIG_FILE),
             '"""', "",
             "# (window title, or its start if is_prefix; icon path in the theme folder)",
             "WINDOW_ICONS = ["]
    lines += ["    (%r, %r, %r)," % rule for rule in rules]
    lines.append("]")
    WINDOW_ICONS_GEN.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote %s (%d window rules)" % (rel(WINDOW_ICONS_GEN), len(rules)))


def main():
    config = load_config()
    color_values = colors(config)
    definition_values = definitions(config, color_values)
    icon_roles = icon_colors(config, color_values, definition_values)
    build_arrow_icons(icon_roles)
    build_indicator_icons(icon_roles)
    icon_config = build_ida_icons(color_values, definition_values)
    build_window_icons(icon_config)
    build_icon_meta()


def build_icon_meta():
    """src/ida/icon_meta_gen.py from src/ida/icon_meta.yaml: the icons the
    plugin maps by action (`map_by_action: true`, icons IDA loads without a
    name). The others are found by path at runtime."""
    unnamed = [(icon.path, icon.actions) for icon in load_icon_meta() if icon.map_by_action and icon.actions]
    lines =['"""Icons IDA loads without a name, matched by action.',
             "",
             "Generated by scripts/build-icons.py from %s -- do not edit." % rel(ICON_META_FILE),
             '"""', "",
             "# (path, actions showing it)",
             "UNNAMED_ICONS = ["]
    lines += ["    (%r, %r)," % item for item in unnamed]
    lines.append("]")
    ICON_META_GEN.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print("wrote %s (%d unnamed icons)" % (rel(ICON_META_GEN), len(unnamed)))


if __name__ == "__main__":
    run(main)
