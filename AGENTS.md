# AGENTS.md

Guide for agents working on this repo: a Catppuccin theme for IDA 9.x
(Windows), made of a Qt style sheet theme, generated SVG icons and an
IDAPython plugin. See README.md for the user-facing setup.

## Ground rules

- **Ask before touching the user's IDA.** Do not run `./x install`,
  `./x uninstall`, `./x dump-icons` or start `ida.exe` (including batch
  `-A -S` runs) without the user's OK. Build into `dist/` and say what to
  install; the user tests in IDA themselves.
- Edit sources, never generated files (see "Generated, do not edit").
- Keep the checks green: `./x check-css` and `uvx pyright` (0 errors).

## Commands

Run scripts through the wrappers, `./x <name> [args]` (sh) or
`./x.ps1 <name> [args]` (PowerShell), which run `uv run scripts/<name>.py`.
Any new `scripts/<name>.py` is picked up automatically. `task` targets in
Taskfile.yml chain them.

| Command | Does |
|---|---|
| `./x link-ida [dir]` | finds IDA (highest `C:\Program Files\IDA Professional <ver>`, or `$IDADIR`, or `dir`), writes `.venv/.../ida.pth` (so editors see `ida_*`) and `.cache/IDA_LOCATION.txt` |
| `./x check-css` | validates `src/css/` against `config.yaml` (rules below) |
| `./x build-css` | `dist/themes/catppuccin/theme.css` and `src/color_gen.py` |
| `./x build-icons` | `dist/themes/catppuccin/icons/` (arrows, menu icons) and `.cache/ida_codicon.html` preview |
| `./x build` | bundles `src/*.py` into `dist/plugins/catppuccin.py` (needs `build-css` first, for `color_gen.py`) |
| `./x install [dir]` / `./x uninstall [dir]` | copy/remove `dist/` into IDA's user dir (default `%APPDATA%\Hex-Rays\IDA Pro`) |
| `./x dump-icons` | runs IDA headless to list its built-in icons into `src/icons.txt`; preview in `.cache/ida_icon_dump.html` |
| `./x extract-modifiers` | regenerates `src/icons/modifier-*.svg` from codicon badges |
| `./x render-icons <folder>` | HTML preview of every SVG under a folder (`dist/test_icons.html`) |

Full build: `check-css`, `build-css`, `build-icons`, `build` (= `task build`).

## Layout

```
config.yaml              colours: palette, tints, definitions, roles
config-icons-ida.yaml    IDA icon name -> codicon base, colour, modifier
src/
  main.py                plugin entry (PLUGIN_ENTRY); merges the parts below
  hexrays.py             re-tags Hex-Rays pseudocode (see "Pseudocode")
  chrome.py              Windows title bars, nav band arrows, faded disabled icons, list row icons
  color_gen.py           GENERATED (gitignored) colours for the plugin
  css/                   theme CSS sources, bundled in src/styles.txt order
    widgets.css          Qt widgets
    highlight.css        syntax colours (listing, xrefs, output, script editor)
    ida_views.css        IDA view decorations (backgrounds, gutter, diff, debugger, graphs, nav band)
    icons_*.css          rules that only set images
  styles.txt             CSS files to bundle, in order
  icons.txt              IDA's replaceable icon names (from dump-icons)
  icons/modifier-*.svg   badge overlays for icons (from extract-modifiers)
scripts/
  <name>.py              commands for ./x
  common/                shared helpers (paths, config, styles, errors, ida, ...)
  ida/                   scripts that run *inside* IDA (not ./x commands)
dist/                    build output; mirrors IDA's user dir (plugins/, themes/catppuccin/)
.cache/                  local state and previews (gitignored)
node_modules/            @vscode/codicons (pnpm)
```

## Colours: config.yaml and the CSS

Every colour is a generated `@def` named `ctp-<kind>-<name>`:

- `ctp-c-*` colours: `palette` (hex only) and `tints` (computed: `amount` =
  blend onto `onto`, default `c-base`; or `alpha` = translucent rgba).
- `ctp-d-*` definitions: shared aliases; may only point at `c-`.
- `ctp-r-*` roles: one per place a colour is used; may only point at `c-` or
  `d-` (never another role, so nothing chains). Nested in the yaml and joined
  with `--`: `roles.widget.menu.bg` is `ctp-r-widget--menu--bg`. Plain names
  must not contain `--`.

Rules enforced by `./x check-css`:

- CSS in `src/css/` references only `${ctp-r-...}` (or an `@def` declared in
  the CSS itself). Never `ctp-c-`/`ctp-d-` or raw colours.
- Each role is used exactly once, and every CSS role in the yaml is used.
  Adding a colour to the CSS means adding a role to `config.yaml`.
- No `${` inside a CSS comment: IDA's preprocessor expands it there too and
  fails on undefined names.

Role namespaces not meant for CSS are listed in `ROLE_TARGETS`
(`scripts/common/config.py`): `titlebar` goes to `src/color_gen.py` for the
plugin, `arrows` to the arrow icons. Everything else is CSS.

The generated definitions block goes first in `theme.css` (with
`@importtheme "_base";`), then `src/styles.txt` files, then the generated
`IDAMainWindow { qproperty-themeicon-* }` block from `src/icons.txt`.

## Icons

- Built-in IDA icons are replaced via `qproperty-themeicon-<Name>`. Only names
  IDA's `themes/_base/theme.css` declares work (about 212). Numbered icons
  (`177.svg`, ...) cannot be replaced: not via CSS, and not by re-registering
  Qt resources (the first registration wins, IDA's comes first).
- Each icon = codicon `base` in a colour + optional `modifier` badge from
  `src/icons/modifier-*.svg`, with the base masked away around the badge
  (circle at 11.5,11.5, gap radius 5.5; see `scripts/common/codicons.py`).
  Codicons are 16x16; a few use a 24 grid and are scaled.
- IDA's own icons are 32x32 SVGs drawn at 16px; previews show 16px and 64px.
- Arrow icons (combo boxes, menus, trees, nav band) are generated from
  `roles.arrows`; Qt draws these black unless every arrow sub-control has an image.
- `themeicon` only reaches actions (menus, toolbar). Window icons, dock
  headers, Windows-menu entries and list rows come from IDA's icon table, and
  some icons load straight from other resources (`:/IDAG/resources/widgets/`,
  e.g. Local Types rows). The plugin swaps list row icons at runtime
  (`_IconSwap` in `src/chrome.py`, via a replacement item delegate),
  recognising originals by their exact pixels: it maps
  `icons/menu/<Name>.svg` to `:/IDAG/resources/menu/<Name>.svg` and
  `icons/swapped/<path>.svg` to `:/<path>.svg`. The latter come from the
  `swapped` section of `config-icons-ida.yaml`, keyed by resource path.
  Lookup tables are built lazily per screen scale: the scale is not known yet
  when the plugin loads. Window icons (dock headers `DockWidgetTitle`, tabbed
  docks `DockTabBar`, the Windows menu) are not swapped yet: setting icons or
  painting over them by pixel match proved unreliable, since IDA re-applies them.

## Plugin

`./x build` inlines `src/main.py` and the `src/` modules it imports into one
file. Rules: import src modules as `from module import name` (never
`import module`); top-level names unique across modules; `*_gen` modules are
generated and must exist (run `build-css`). The plugin is `PLUGIN_FIX` (loads
at IDA startup) and does nothing unless the catppuccin theme is active
(detected from the theme's icon paths in the app style sheet).

Pseudocode: Hex-Rays reuses colour tags (keywords and numbers share one,
members and operators share one, function names and globals share one, a
declaration is one span). `hexrays.py` re-tags each printed line so every
token kind lands on its own tag; the "pc:" comments in `highlight.css` /
`config.yaml` say which IDA property colours which pseudocode token.

Things a style sheet cannot reach, handled in `chrome.py`:
- Title bar colours via DWM (Windows 11; dark mode only on 10).
- Nav band scroll buttons: IDA sets their icon in code after the theme loads.
- Disabled icons: Qt derives them by remapping grey around the window colour
  (light icons stay light on dark). A `QProxyStyle` fades them instead. It is
  inserted on top of whatever style is active (IDA's own proxy over
  windowsvista, or a user's style); never replace the style by name.

## Testing without IDA

- `uvx pyright` type-checks `src/` and `scripts/` (needs `./x link-ida` for `ida_*`).
- The dev venv has PySide6 pinned to the version IDA bundles (6.8.0), so Qt
  behaviour (style sheets, QtSvg rendering incl. masks, styles) can be tried
  in `uv run python` with a `QApplication`. Use scoped enums
  (`QIcon.Mode.Disabled`) so pyright accepts them.
- Check icons in the HTML previews (`.cache/ida_codicon.html`, `./x render-icons`).

## Gotchas

- Styling `QToolButton` at all makes Qt stop reserving room for the menu
  part of `popupMode="1"` buttons; keep the `padding-right` rule in sync with
  `::menu-button` width.
- With a style sheet active, `QApplication.style()` is an unnamed
  `QStyleSheetStyle`; the real style is its only `QStyle` child.
- Some widgets read `[os-dark-theme="true"]` variants; selectors include both.
- Pin `pyside6-essentials` in pyproject.toml to IDA's bundled PySide6 when
  IDA is upgraded (`<IDA>/python/PySide6/__init__.py`).

## Generated, do not edit

`dist/`, `src/color_gen.py`, `.cache/`. `src/icons.txt` and
`src/icons/modifier-*.svg` are committed but produced by `dump-icons` and
`extract-modifiers`; regenerate rather than hand-edit.
