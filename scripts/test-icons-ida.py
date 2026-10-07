"""
Preview IDA's action icons, original against themed.

    uv run scripts/test-icons-ida.py    -> .cache/ida_icon_test.html

Reads only:
- src/ida/icon_meta.yaml (dump-icons): every icon, its path, its actions;
- .cache/ida-icon-dump/svg/<path> (dump-icons): IDA's originals;
- dist/catppuccin-ida/themes/catppuccin/<path> (the build): the theme's, plus
  its extra/ icons (no IDA original; shown in their own section).

One tile per icon, grouped by folder, showing its actions. A toggle at the
top (always visible; or press T) switches every tile between the original
and the themed icon; hovering an icon shows the theme path it maps to.
Icons mapped by action have no original to show (IDA loads them without a
name). A themed icon missing from the build shows as a red block: the
plugin would leave IDA's icon there.
"""

import base64
import html
import mimetypes
from collections import defaultdict

from common.config import colors, load_config
from common.errors import run
from common.icon_meta import load_icon_meta
from common.paths import DIST_THEME, ICON_DUMP_DIR, IDA_ICON_TEST_PAGE, file_url, rel

ORIGINALS_DIR = ICON_DUMP_DIR / "svg"
EXTRA_DIR = "extra"           # icons IDA has no resource for (config `icons` extra/...)

PAGE = """<!doctype html>
<html>
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>IDA icons: original vs themed</title>
<style>
  :root {{ --bg: {base}; --panel: {mantle}; --fg: {text}; --dim: {subtext}; --line: {surface};
          --accent: {mauve}; --bad: {red}; }}
  * {{ box-sizing: border-box; }}
  body {{ margin: 0; background: var(--bg); color: var(--fg); font: 12px/1.4 system-ui, sans-serif; }}
  header {{ position: sticky; top: 0; z-index: 1; display: flex; flex-wrap: wrap; align-items: center;
            gap: 8px 20px; padding: 10px 16px; background: var(--panel); border-bottom: 1px solid var(--line); }}
  header h1 {{ margin: 0; font-size: 14px; font-weight: 600; }}
  .stats {{ color: var(--dim); }}
  .stats b {{ color: var(--fg); font-weight: 600; }}
  .stats .bad {{ color: var(--bad); }}
  .switch {{ display: inline-flex; border: 1px solid var(--line); border-radius: 6px; overflow: hidden; }}
  .switch button {{ font: inherit; color: var(--dim); background: none; border: 0; padding: 5px 12px;
                    cursor: pointer; }}
  .switch button[aria-pressed="true"] {{ color: var(--bg); background: var(--accent); }}
  .hint {{ color: var(--dim); }}
  main {{ padding: 4px 16px 24px; }}
  h2 {{ font-size: 13px; font-weight: 600; margin: 20px 0 8px; }}
  h2 span {{ color: var(--dim); font-weight: normal; }}
  .grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(150px, 1fr)); gap: 8px; }}
  .tile {{ display: flex; flex-direction: column; gap: 6px; padding: 8px; border: 1px solid var(--line);
           border-radius: 6px; min-width: 0; }}
  .icons {{ display: flex; align-items: center; gap: 12px; height: 64px; }}
  .icons > * {{ flex: none; }}
  .s16 {{ width: 16px; height: 16px; }}
  .s64 {{ width: 64px; height: 64px; }}
  .missing {{ background: var(--bad); border-radius: 2px; }}
  .none {{ border: 1px dashed var(--line); border-radius: 2px; }}
  .name {{ word-break: break-all; color: var(--dim); }}
  .actions {{ word-break: break-word; }}
  .actions.empty {{ color: var(--dim); font-style: italic; }}
  .tag {{ display: inline-block; margin-left: 4px; padding: 0 4px; border: 1px solid var(--line);
          border-radius: 4px; color: var(--dim); font-size: 11px; }}
  body.themed .original, body:not(.themed) .themed {{ display: none; }}
</style>
</head>
<body class="themed">
<header>
  <h1>IDA icons</h1>
  <div class="switch" role="group" aria-label="Icons shown">
    <button type="button" data-mode="original" aria-pressed="false">Original</button>
    <button type="button" data-mode="themed" aria-pressed="true">Themed</button>
  </div>
  <span class="hint">T toggles</span>
  <span class="stats"><b>{count}</b> icons &middot; <b>{themed}</b> themed &middot;
    <b class="{missing_class}">{missing}</b> missing from the build &middot; <b>{by_action}</b> mapped by action</span>
</header>
<main>
{sections}
</main>
<script>
  const buttons = document.querySelectorAll(".switch button");
  function show(mode) {{
    document.body.classList.toggle("themed", mode === "themed");
    buttons.forEach(b => b.setAttribute("aria-pressed", String(b.dataset.mode === mode)));
  }}
  buttons.forEach(b => b.addEventListener("click", () => show(b.dataset.mode)));
  document.addEventListener("keydown", e => {{
    if ((e.key === "t" || e.key === "T") && !e.ctrlKey && !e.metaKey && !e.altKey)
      show(document.body.classList.contains("themed") ? "original" : "themed");
  }});
</script>
</body>
</html>
"""

SECTION = """<section>
<h2>{folder} <span>{count}</span></h2>
<div class="grid">
{tiles}
</div>
</section>"""

TILE = """<div class="tile">
  <div class="icons original" title="{original_title}">{original}</div>
  <div class="icons themed" title="{themed_title}">{themed}</div>
  <div class="name">{name}{tag}</div>
  <div class="actions{actions_class}">{actions}</div>
</div>"""


def _data_uri(path):
    mime = mimetypes.guess_type(path.name)[0] or "image/svg+xml"
    return "data:%s;base64,%s" % (mime, base64.b64encode(path.read_bytes()).decode("ascii"))


def _images(path):
    """The icon at 16px and 64px, or None if the file does not exist."""
    if not path.is_file():
        return None
    uri = _data_uri(path)
    return '<img class="s16" src="%s" alt=""><img class="s64" src="%s" alt="">' % (uri, uri)


def _placeholder(css_class):
    return '<div class="s16 %s"></div><div class="s64 %s"></div>' % (css_class, css_class)


def main():
    icons = load_icon_meta()
    palette = colors(load_config())
    folders = defaultdict(list)
    themed_count = missing_count = 0
    for icon in icons:
        theme_path = "themes/catppuccin/" + icon.path
        themed = _images(DIST_THEME / icon.path)
        if themed is None:
            missing_count += 1
            themed = _placeholder("missing")
            themed_title = "%s\nmissing from the build: IDA's icon stays" % theme_path
        else:
            themed_count += 1
            themed_title = theme_path
        if icon.map_by_action:
            original = _placeholder("none")
            original_title = "%s\nmapped by action: IDA loads the original without a name" % theme_path
        else:
            original = _images(ORIGINALS_DIR / icon.path) or _placeholder("missing")
            original_title = "%s\noriginal: :/<prefix>/%s" % (theme_path, icon.path)
        folder, _, name = icon.path.rpartition("/")
        folders[folder].append(TILE.format(
            original=original, original_title=html.escape(original_title),
            themed=themed, themed_title=html.escape(themed_title),
            name=html.escape(name),
            tag='<span class="tag">by action</span>' if icon.map_by_action else "",
            actions=html.escape(", ".join(icon.actions)) if icon.actions else "no actions",
            actions_class="" if icon.actions else " empty"))

    # Extra icons IDA has no resource for: whatever the build put in extra/
    for file in sorted((DIST_THEME / EXTRA_DIR).glob("**/*.svg")):
        path = file.relative_to(DIST_THEME).as_posix()
        folder, _, name = path.rpartition("/")
        folders[folder].append(TILE.format(
            original=_placeholder("none"),
            original_title=html.escape("themes/catppuccin/%s\nextra: IDA has no original" % path),
            themed=_images(file), themed_title=html.escape("themes/catppuccin/" + path),
            name=html.escape(name), tag='<span class="tag">extra</span>',
            actions="used by the plugin / CSS", actions_class=" empty"))

    sections =[SECTION.format(folder=html.escape(folder), count=len(tiles), tiles="\n".join(tiles))
                for folder, tiles in sorted(folders.items())]
    page = PAGE.format(
        base=palette["base"], mantle=palette["mantle"], text=palette["text"], subtext=palette["subtext0"],
        surface=palette["surface0"], mauve=palette["mauve"], red=palette["red"],
        count=len(icons), themed=themed_count, missing=missing_count,
        missing_class="bad" if missing_count else "",
        by_action=sum(1 for icon in icons if icon.map_by_action),
        sections="\n".join(sections))
    IDA_ICON_TEST_PAGE.parent.mkdir(parents=True, exist_ok=True)
    IDA_ICON_TEST_PAGE.write_text(page, encoding="utf-8", newline="\n")
    print("%d icons: %d themed, %d missing from %s" % (len(icons), themed_count, missing_count, rel(DIST_THEME)))
    print("wrote %s" % file_url(IDA_ICON_TEST_PAGE))


if __name__ == "__main__":
    run(main)
