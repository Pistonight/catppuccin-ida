"""
Action icons (toolbar, menus): IDA 9.4 only accepts its own built-in resource
paths in `qproperty-themeicon-*` (anything else blanks the icon), so the
theme's icons are set on the actions through the SDK instead.
"""

import time

import ida_kernwin

from ida.icon_meta_gen import UNNAMED_ICONS

# Actions are only looked for after events that register them (_ActionIconHooks);
# this catches the rest (e.g. a script registering one later).
ACTION_SCAN_FALLBACK_S = 10
# Print the icons actions show that the theme has no version of (by the
# path the theme's version would have, or #<id> for an unnamed icon the icon
# meta does not know), with the actions showing them; e.g. new ones, or
# other plugins'.
REPORT_MISSING_ICONS = True


class ActionIcons:
    """Gives every action showing one of IDA's icons the theme's version of
    it (see chrome_icon_resources.py and src/ida/icon_meta.yaml), found one
    of two ways:

    - icons in IDA's icon table, by path: the action's icon id is a table
      entry, whose path IconResources knows.
    - icons IDA loads without a name (e.g. the Git actions'), by action:
      nothing maps their id back to a file, so icon_meta lists the actions
      (UNNAMED_ICONS, `map_by_action`).

    Icons the theme has no version of are reported (REPORT_MISSING_ICONS).
    Actions registered later (Hex-Rays, the debugger, plugins) are picked up
    by refresh(). Listing every action each time costs, so refresh() only
    does it after an event that may have registered some (see
    _ActionIconHooks), or ACTION_SCAN_FALLBACK_S after the last scan."""

    def __init__(self, resources):
        self.resources = resources       # IconResources
        self.unnamed = {}                # action -> (path, theme file or None)
        for path, actions in UNNAMED_ICONS:
            for action in actions:
                self.unnamed[action] = (path, resources.theme_file(path))
        self.loaded = {}             # theme file -> custom icon id (loaded on first use)
        self.replaced = {}           # action -> its original icon id
        self.seen = set()            # actions already looked at
        self.reported = set()        # missing icons already reported
        self.stale = True            # actions may have been registered since the last scan
        self.last_scan = 0.0
        self.hooks = _ActionIconHooks(self)
        self.hooks.hook()

    def mark_stale(self):
        self.stale = True

    def refresh(self):
        now = time.monotonic()
        if not self.stale and now - self.last_scan < ACTION_SCAN_FALLBACK_S:
            return
        self.stale = False
        self.last_scan = now
        missing = {}                 # what the theme lacks -> [action]
        for action in ida_kernwin.get_registered_actions():
            if action in self.seen:
                continue
            self.seen.add(action)
            ok, original = ida_kernwin.get_action_icon(action)
            if not ok or original < 0:
                continue
            if original in self.resources.table:
                name = self.resources.table[original]
                file = self.resources.theme_file(name)
            elif action in self.unnamed:
                name, file = self.unnamed[action]
            else:
                name, file = "#%d (unnamed, not in the icon meta)" % original, None
            custom = self._custom_icon(file) if file is not None else None
            if custom is not None and ida_kernwin.update_action_icon(action, custom):
                self.replaced[action] = original
            else:
                missing.setdefault(name, []).append(action)
        if REPORT_MISSING_ICONS:
            self._report(missing)

    def _report(self, missing):
        """Print the icons the theme has no version of, once each (an icon
        reported before is only listed again with its newly seen actions)."""
        if not missing:
            return
        print("catppuccin: no theme icon for %d icons, IDA's kept: %s" % (len(missing), "; ".join(
            "%s%s (%s)" % (name, "" if name not in self.reported else " (more)", ", ".join(sorted(actions)))
            for name, actions in sorted(missing.items()))))
        self.reported.update(missing)

    def _custom_icon(self, file):
        if file not in self.loaded:
            custom = ida_kernwin.load_custom_icon(file)
            self.loaded[file] = custom if custom > 0 else None
        return self.loaded[file]

    def stop(self):
        """Give the actions back their original icons and free the theme's."""
        self.hooks.unhook()
        registered = set(ida_kernwin.get_registered_actions())
        for action, original in self.replaced.items():
            if action in registered:
                ida_kernwin.update_action_icon(action, original)
        for custom in self.loaded.values():
            if custom is not None:
                ida_kernwin.free_custom_icon(custom)
        self.replaced.clear()
        self.loaded.clear()
        self.seen.clear()


class _ActionIconHooks(ida_kernwin.UI_Hooks):
    """Marks the action icons stale on the events that register actions
    (IDA has no hook for a single action); the scan itself waits for the
    next refresh, so a burst of events costs one scan."""

    def __init__(self, icons):
        super().__init__()
        self.icons = icons

    def ready_to_run(self):
        self.icons.mark_stale()

    def database_inited(self, is_new_database, idc_script):
        self.icons.mark_stale()

    def plugin_loaded(self, plugin_info):
        self.icons.mark_stale()

    def debugger_menu_change(self, enable):
        self.icons.mark_stale()

    def widget_visible(self, widget):
        self.icons.mark_stale()
