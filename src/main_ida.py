"""
Catppuccin for IDA 9.x: the runtime half of the catppuccin theme.

- re-tags Hex-Rays pseudocode so each kind of token can have its own colour
- colours Windows title bars and the nav band scroll arrows

Does nothing unless the catppuccin theme is active in IDA's GUI: not in
text mode / idalib (no GUI to theme), and not if the environment variable
CATPPUCCIN_DISABLE is 1 (set by ./x dump-icons, to see IDA's own icons).

Install: copy this file to %APPDATA%\\Hex-Rays\\IDA Pro\\plugins\\
"""

import os

import ida_idaapi
import ida_kernwin

from ida.chrome import Chrome, theme_dir
from ida.hexrays import Retagger
from perf import perf

DISABLE_ENV = "CATPPUCCIN_DISABLE"


class _UiHooks(ida_kernwin.UI_Hooks):
    def __init__(self, retagger):
        super().__init__()
        self.retagger = retagger

    def database_inited(self, is_new_database, idc_script):
        self.retagger.start()

    def database_closed(self):
        self.retagger.stop()


class CatppuccinPlugin(ida_idaapi.plugin_t):
    # PLUGIN_FIX: load at startup, so title bars are styled before any
    # database is open; the decompiler hooks attach once one is.
    flags = ida_idaapi.PLUGIN_FIX | ida_idaapi.PLUGIN_HIDE
    comment = "Catppuccin pseudocode colours and window chrome"
    help = ""
    wanted_name = "Catppuccin"
    wanted_hotkey = ""

    # Set by init() only when the theme is active; IDA calls term() even
    # after init() returned PLUGIN_SKIP.
    chrome: Chrome | None = None
    retagger: Retagger | None = None
    ui_hooks: _UiHooks | None = None

    def init(self):
        # Checked before anything touches Qt: headless IDA has no QApplication.
        if os.environ.get(DISABLE_ENV) == "1" or not ida_kernwin.is_idaq():
            return ida_idaapi.PLUGIN_SKIP
        with perf.measure("init: total", report=True):
            directory = theme_dir()
            if directory is None:
                return ida_idaapi.PLUGIN_SKIP
            perf.start()
            self.chrome = Chrome(directory)
            with perf.measure("init: pseudocode hooks", report=True):
                self.retagger = Retagger()
                self.retagger.start()
            self.ui_hooks = _UiHooks(self.retagger)
            self.ui_hooks.hook()
            return ida_idaapi.PLUGIN_KEEP

    def run(self, arg):
        pass

    def term(self):
        if self.ui_hooks is not None:
            self.ui_hooks.unhook()
        if self.retagger is not None:
            self.retagger.stop()
        if self.chrome is not None:
            self.chrome.stop()
        perf.stop()


def PLUGIN_ENTRY():
    return CatppuccinPlugin()
