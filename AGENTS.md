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
A shell script `scripts/<name>` (no extension, for `./x`) or
`scripts/<name>.ps1` (for `./x.ps1`) takes priority over the `.py`. New
scripts are picked up automatically. Several scripts can be
chained, `./x clean build install`: they run in order and
stop at the first failure; an argument that names a script starts the next
step, any other goes to the script before it. `task` targets in
Taskfile.yml chain them.

| Command | Does |
|---|---|
| `./x setup-ida` | writes `.venv/.../ida.pth` (so editors see `ida_*`) for the IDA install from `ida_dir()` (`scripts/common/paths.py`): `Paths.ida-install-dir` in `%APPDATA%\Hex-Rays\IDA Pro\ida-config.json` if set; else `.cache/IDA_LOCATION.txt` if usable; else the highest `C:\Program Files\IDA Professional <ver>`; else it asks and records the answer in `.cache/IDA_LOCATION.txt`. Scripts that need IDA call it themselves |
| `./x check-css` | validates `src/css/` against `config.yaml` (rules below) |
| `./x build-css` | `dist/catppuccin-ida/themes/catppuccin/theme.css` and `src/color_gen.py` |
| `./x build-icons` | `dist/catppuccin-ida/themes/catppuccin/icons/` (arrows, indicators), `themes/catppuccin/<path>` for each entry of `config-icons-ida.yaml` `icons` (warns about `icon_meta.yaml` icons with no entry), `src/ida/icon_meta_gen.py` and `.cache/ida_codicon.html` preview |
| `./x build-py` | bundles `src/*.py` into `dist/catppuccin-ida/plugins/catppuccin.py` (needs `build-css` and `build-icons` first, for the `*_gen.py`) |
| `./x package` | zips the contents of `dist/catppuccin-ida/` into `dist/catppuccin-ida.zip` (unpacks into an IDA user dir) |
| `./x install [dir]` / `./x uninstall [dir]` | copy/remove `dist/catppuccin-ida/` into IDA's user dir (default `%APPDATA%\Hex-Rays\IDA Pro`) |
| `./x dump-icons` | runs IDA headless (plugin off, `CATPPUCCIN_DISABLE=1`) to write the icons IDA's actions show to `src/ida/icon_meta.yaml` (and resource copies to `.cache/ida-icon-dump/`) |
| `./x extract-modifiers` | regenerates `src/icons/modifier-*.svg` from codicon badges |
| `./x setup` | `scripts/setup` / `scripts/setup.ps1`: `pnpm install` and `uv sync` |
| `./x clean` | `scripts/clean` / `scripts/clean.ps1`: deletes `dist/`, `.cache/`, `.venv/`, `__pycache__/` and `node_modules/` (`pnpm clean`) |
| `./x test-icons-ida` | `.cache/ida_icon_test.html`: every icon in `src/ida/icon_meta.yaml`, original (`.cache/ida-icon-dump/svg/`) vs themed (`dist/.../themes/catppuccin/<path>`) behind an always-visible toggle (T); hover shows the theme path, tiles list the actions; red block = missing from the build, empty original = mapped by action. Run after `build` and `dump-icons` |
| `./x render-icons <folder>` | HTML preview of every SVG under a folder (`dist/test_icons.html`) |

Full build: `./x build` (`scripts/build` / `build.ps1`) runs `check-css`, `build-css`, `build-icons`, `build-py`; it stops at the first failure.

## Layout

```
config.yaml              colours: palette, tints, definitions, roles
config-icons-ida.yaml    `icons`: icon path (from src/ida/icon_meta.yaml, or extra/<name>.svg) -> codicon base,
                         colour, modifier; `windows`: dock window title -> icon path;
                         `actions`: action name -> icon path (overrides)
src/
  main_ida.py            IDA plugin entry (PLUGIN_ENTRY); merges the parts below
  ida/                   IDA plugin modules, imported as `ida.<name>`
    hexrays.py           re-tags Hex-Rays pseudocode (see "Pseudocode")
    chrome.py            Windows title bars, nav band arrows
    chrome_icon_resources.py  IconResources: IDA's icon resources by path, the theme's versions
    chrome_action_icons.py    ActionIcons: toolbar/menu icons, set on the actions
    chrome_icon_swap.py       IconSwap: list row icons, recognised by pixels
    chrome_window_icons.py    WindowIcons: dock window icons by title, header buttons by tooltip
    chrome_faded_disabled_icons.py  FadedDisabledIcons: disabled icons faded, not greyed
    icon_meta.yaml       icons IDA's actions show (from dump-icons); icon_meta_gen.py is built from it
    old_chrome_icon_hack.py  IDA 9.3 list row / dock window icon swaps; not imported, kept for reference
  perf.py                timings printed to IDA's output (PERF_ENABLED)
  color_gen.py           GENERATED (gitignored) colours for the plugin
  css/                   theme CSS sources, bundled in src/styles.txt order
    widgets.css          Qt widgets
    highlight.css        syntax colours (listing, xrefs, output, script editor)
    ida_views.css        IDA view decorations (backgrounds, gutter, diff, debugger, graphs, nav band)
    icons_*.css          rules that only set images
  styles.txt             CSS files to bundle, in order
  icons/modifier-*.svg   badge overlays for icons (from extract-modifiers)
scripts/
  <name>.py              commands for ./x
  common/                shared helpers: paths.py (every repo, dist, cache and IDA path), config, codicons, render, errors
  tools/                 building blocks the scripts call (not ./x commands):
                         python_bundler.py: bundle_python_modules(entry_point)
                         css_bundler.py: bundle_css_files(list_txt), paths relative to the txt
  ida/                   scripts that run *inside* IDA (not ./x commands)
dist/                    build output, one folder per target
  catppuccin-ida/        the IDA build; mirrors IDA's user dir (plugins/, themes/catppuccin/)
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
`@importtheme "_base";`), then `src/styles.txt` files. `theme.css` sets no
`qproperty-themeicon-*` (see "Icons").

## Icons

- Toolbar/menu (action) icons are set by the plugin, not the CSS. IDA 9.4
  still hands each `qproperty-themeicon-<Name>` to its main window, but loads
  the value with `load_icon()`, which only resolves `:/<prefix>/<path>`
  resources in a table IDA builds from its own resource folders; it keeps
  only the table index, so a file path (index -1) blanks the icon. The plugin
  (`ActionIcons` in `src/ida/chrome_action_icons.py`, over `IconResources` in
  `src/ida/chrome_icon_resources.py`) sets them per action
  (`update_action_icon`; ids are not stable, actions are), finding the
  theme's version two ways, per `src/ida/icon_meta.yaml` (entries `path`,
  `actions`, optional `map_by_action: true`, sorted by path):
  - by path (icons in IDA's icon table): at startup the plugin
    walks IDA's Qt resources and asks `get_icon_id_by_name` for each key
    (the path without `:/<prefix>/`: `:/IDAG/resources/menu/X.svg` ->
    `resources/menu/X.svg`), giving id -> key; an action showing that id
    gets the theme's version. Needs no data at runtime.
  - `map_by_action: true` (icons IDA loads without a name, e.g. the
    Git/Teams actions', drawn from `:/HVUI/resources/icons/git/`): nothing
    maps the id back to a file, so the plugin matches the listed `actions`
    (built into `src/ida/icon_meta_gen.py` by `build-icons`); their path is
    just a file name, `action_ids/<id>.svg` (the id when dumped; ids are not
    stable, so a new dump may rename them).
  Either way the theme's version is `themes/catppuccin/<path>` (e.g.
  `resources/menu/X.svg`, `action_ids/664.svg`): table paths drop the
  `:/<prefix>/`, and no two resources share one.
  Theme files are loaded on first use (`load_custom_icon`); icons without
  one are printed as missing (`REPORT_MISSING_ICONS`). `build-icons` writes
  them from the `icons` section of `config-icons-ida.yaml`, keyed by path; its
  other top-level entries (names, `swapped`, `windows`, `plugin`: the 9.3
  layout) are ignored. New actions (Hex-Rays,
  debugger, plugins) and icons IDA changes at runtime (`SetDirection`
  up/down, the `Analysis` indicator, the Windows menu's `WindowActivate<n>`)
  are both caught because every pass re-checks every action's current icon
  (skipping the theme's own custom ids); a pass over ~860 actions takes
  ~1 ms. Passes run on the 1 s refresh and, rate-limited to
  `ACTION_SCAN_MIN_S`, after the `updated_actions` UI hook (and
  `ready_to_run`, `database_inited`, `plugin_loaded`, `debugger_menu_change`,
  `widget_visible`); `stop()` restores and frees them. The same APIs exist in 9.3. Without the plugin
  (or with `CATPPUCCIN_DISABLE=1` in the environment), IDA's stock icons show.
- Dumping: `./x dump-icons` runs IDA headless (plugin off) on a stub
  binary with `scripts/ida/dump_icons.py`, which writes
  `src/ida/icon_meta.yaml` (committed; regenerate, don't edit) and copies
  of the resource images to `.cache/ida-icon-dump/` (`svg/` table icons,
  `untabled/` the rest, `icons.txt` menu names, `summary.txt`, which also
  lists resources that would share a path once the prefix is dropped).
  Icons can't be replaced via CSS outside the table, nor by re-registering
  Qt resources (the first registration wins, IDA's comes first).
- Each icon = codicon `base` in a colour + optional `modifier` badge from
  `src/icons/modifier-*.svg`, with the base masked away around the badge
  (codicon badge circle at 11.5,11.5 r 4.5, see `scripts/common/codicons.py`;
  drawn at `BADGE_SCALE` (0.8) towards the bottom-right corner, with a 1 px gap,
  see `scripts/build-icons.py`).
  Codicons are 16x16; a few use a 24 grid and are scaled.
- IDA's own icons are 32x32 SVGs drawn at 16px; previews show 16px and 64px.
- Arrow icons (combo boxes, menus, trees, nav band) are generated from
  `roles.arrows`; Qt draws these black unless every arrow sub-control has an image.
- Action icons only reach menus and the toolbar. Window icons, dock
  headers, Windows-menu entries and list rows come from IDA's icon table, and
  some icons load straight from other resources (`:/IDAG/resources/widgets/`,
  e.g. Local Types rows). The 9.3 plugin swapped list row icons at runtime
  (`_IconSwap`, now in `src/ida/old_chrome_icon_hack.py` and not loaded, via a
  replacement item delegate),
  recognising originals by their exact pixels: it maps
  `icons/menu/<Name>.svg` to `:/IDAG/resources/menu/<Name>.svg` and
  `icons/swapped/<path>.svg` to `:/<path>.svg`. The latter come from the
  `swapped` section of `config-icons-ida.yaml`, keyed by resource path.
  Lookup tables are built per screen scale (not known yet when the plugin
  loads) from the 1 s refresh, in slices of at most `TABLE_SLICE_MS`: built
  in one go it took ~260 ms and froze IDA (a white flash) on the first list.
- Dock window icons (`WindowIcons` in `src/ida/chrome_window_icons.py`) are
  matched by window title: the `windows` section of `config-icons-ida.yaml`
  maps titles (trailing `*` = any suffix) to icon paths in `icons`, generated
  into `src/ida/window_icons_gen.py`. They are set on `IDADockWidget`
  (window icon), `DockTabBar` tabs (tabbed docks) and painted over the icon
  label of `DockWidgetTitle` (header of a dock alone in its area); the Close /
  Fullscreen / Float buttons of both `DockWidgetTitle` and
  `DockAreaDragTitle` (header of an area of tabbed docks), matched by tooltip
  (`DOCK_BUTTON_ICONS`), get `extra/window-*.svg`; tab close buttons get it
  from `QTabBar::close-button` in `icons_indicator.css`. IDA re-applies its
  icons, so tab bars and buttons are fixed up on every paint. Entries in the
  Windows menu (a `QMenu` titled "Windows", entries named after the window
  titles) are fixed up on its Show event, after IDA refills it. Docks are
  looked for after the `widget_visible` / `widget_invisible` /
  `current_widget_changed` UI hooks, or every `DOCK_SCAN_FALLBACK_S` (2 s).
- The `actions` section of `config-icons-ida.yaml` maps an action name to
  an icon path in `icons`, set on that action whatever icon it shows (e.g.
  `CpuregsOpenRegDisasm`, which shares `WindowOpen` with `WindowOpen`). It is
  generated into `ACTION_ICONS` in `src/ida/icon_meta_gen.py` (with
  `UNNAMED_ICONS`); `ActionIcons` checks it first. An action missing from
  `icon_meta.yaml` only warns (it may come from another plugin).
- `extra/<name>.svg` entries in `icons` are icons IDA has no resource for
  (dock header buttons, Microcode window); the build accepts them without a
  metadata entry, and `test-icons-ida` shows them in their own section.

## Plugin

`./x build-py` inlines `src/main_ida.py` and the `src/` modules it imports into one
file (via `scripts/tools/python_bundler.py`). Module names are rooted at
`src/` (`src/ida/chrome.py` is `ida.chrome`). Rules: import src modules as
`from module import name`, e.g. `from ida.chrome import Chrome` (never
`import module` or `from ida import chrome`); top-level names unique across modules; `*_gen` modules are
generated and must exist (run `build-css`). The plugin is `PLUGIN_FIX` (loads
at IDA startup) and does nothing unless the catppuccin theme is active
(detected from the theme's icon paths in the app style sheet).

Pseudocode: Hex-Rays reuses colour tags (keywords and numbers share one,
members and operators share one, function names and globals share one, a
declaration is one span). `ida/hexrays.py` re-tags each printed line so every
token kind lands on its own tag; the "pc:" comments in `highlight.css` /
`config.yaml` say which IDA property colours which pseudocode token.

Things a style sheet cannot reach, handled in `ida/chrome.py`:
- Title bar colours via DWM (Windows 11; dark mode only on 10).
- Nav band scroll buttons: IDA sets their icon in code after the theme loads.

and in `ida/chrome_*.py` modules, one per class (`Chrome` creates them):
- Toolbar/menu icons (`chrome_action_icons.py`): set on the actions through
  the SDK (see "Icons").
- List row icons (`chrome_icon_swap.py`): rows (Local Types, Functions, ...)
  load icons straight from resources, no action involved, and a QIcon does
  not tell its source, so originals are recognised by pixels: each icon the
  theme has (`<theme>/<path>`) is rendered from `:/<prefix>/<path>` into a
  fingerprint table (per screen scale, built in `TABLE_SLICE_MS` slices),
  and views with a plain `QStyledItemDelegate` get `IconSwapDelegate`, which
  swaps matching row icons as they draw (cached per `QIcon.cacheKey`). The
  same lookup fixes menu entries whose icon IDA sets directly, with no
  action behind it (submenus: Edit > Strings shows the current string type,
  Operand type > Offset / Number): menus get an event filter that swaps
  their entries' icons on Show, after IDA refilled them. Views and menus
  are looked for after the `widget_visible` UI hook, or every
  `VIEW_SCAN_FALLBACK_S` (10 s).
- Disabled icons (`chrome_faded_disabled_icons.py`): Qt derives them by remapping grey around the window colour
  (light icons stay light on dark). A `QProxyStyle` fades them instead. It is
  inserted on top of whatever style is active (IDA's own proxy over
  windowsvista, or a user's style); never replace the style by name.

## Testing without IDA

- `uvx pyright` type-checks `src/` and `scripts/` (needs `./x setup-ida` for `ida_*`).
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
- In a paint event filter, don't look up the painted widget's siblings
  (`findChildren` on its parent): it re-wraps the widget and PySide raised
  "Internal C++ object already deleted" in IDA. Gather what painting needs
  beforehand (the header icon label gets its title as a property in refresh).
- Some widgets read `[os-dark-theme="true"]` variants; selectors include both.
- Pin `pyside6-essentials` in pyproject.toml to IDA's bundled PySide6 when
  IDA is upgraded (`<IDA>/python/PySide6/__init__.py`).

## Generated, do not edit

`dist/`, `src/*_gen.py`, `.cache/`. `src/ida/icon_meta.yaml` and
`src/icons/modifier-*.svg` are committed but produced by `dump-icons` and
`extract-modifiers`; regenerate rather than hand-edit.
