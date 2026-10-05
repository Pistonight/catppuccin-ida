"""
Catppuccin for IDA 9.x: the runtime half of the catppuccin theme.

- re-tags Hex-Rays pseudocode so each kind of token can have its own colour
- colours Windows title bars and the nav band scroll arrows

Does nothing unless the catppuccin theme is active.

Install: copy this file to %APPDATA%\\Hex-Rays\\IDA Pro\\plugins\\
"""

import ida_idaapi
import ida_kernwin

from chrome import Chrome, theme_dir
from hexrays import Retagger


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

    def init(self):
        directory = theme_dir()
        if directory is None:
            return ida_idaapi.PLUGIN_SKIP
        self.chrome = Chrome(directory)
        self.retagger = Retagger()
        self.retagger.start()
        self.ui_hooks = _UiHooks(self.retagger)
        self.ui_hooks.hook()
        return ida_idaapi.PLUGIN_KEEP

    def run(self, arg):
        pass

    def term(self):
        self.ui_hooks.unhook()
        self.retagger.stop()
        self.chrome.stop()


def PLUGIN_ENTRY():
    return CatppuccinPlugin()
