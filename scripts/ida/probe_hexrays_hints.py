"""
Research probe, run inside IDA (File > Script file... / Alt+F7) with a
pseudocode window open. Running it again turns it off.

Hex-Rays builds its hover hints as plain text, and a hook can only put text
in front of them or replace them. This shows what the type printer can make
instead, coloured: while it is on, every pseudocode hint starts with

    [probe] <what is under the mouse>
    A: the type, coloured, as a declaration
    B: the same with argument locations (functions)
    -------- (then the normal Hex-Rays hint)

Hover a local variable, a struct member, a call through a member pointer, a
function call and a type name, and screenshot the hints. Every hint is also
logged, with its colour tags, to .cache/hexrays_hints_probe.txt.
"""

import os
import traceback

import ida_hexrays
import ida_lines
import ida_typeinf

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
OUT = os.path.join(ROOT, ".cache", "hexrays_hints_probe.txt")
BASE_FLAGS = (ida_typeinf.PRTYPE_MULTI | ida_typeinf.PRTYPE_TYPE | ida_typeinf.PRTYPE_SEMI
              | ida_typeinf.PRTYPE_COLORED)
VARIANTS = (("A", BASE_FLAGS), ("B", BASE_FLAGS | ida_typeinf.PRTYPE_ARGLOCS))


def describe(vu):
    """(summary, type, name) of the item under the mouse."""
    item = vu.item
    if item.citype == ida_hexrays.VDI_LVAR:
        lv = item.l
        loc = ida_hexrays.print_vdloc(lv.location, lv.width)
        return "lvar declaration %s at %s" % (lv.name, loc), lv.type(), lv.name
    if item.citype == ida_hexrays.VDI_FUNC:
        return "function header", item.f.type, ""
    if item.citype != ida_hexrays.VDI_EXPR:
        return "citype %d" % item.citype, None, ""
    e = item.e
    summary = "expr %s" % ida_hexrays.get_ctype_name(e.op)
    name = ""
    if e.op == ida_hexrays.cot_var:
        lv = vu.cfunc.get_lvars()[e.v.idx]
        name = lv.name
        summary += " %s at %s" % (name, ida_hexrays.print_vdloc(lv.location, lv.width))
    elif e.op in (ida_hexrays.cot_memref, ida_hexrays.cot_memptr):
        summary += " off=0x%X" % e.m
    elif e.op == ida_hexrays.cot_obj:
        summary += " ea=0x%X" % e.obj_ea
    return summary, e.type, name


def render(tif, name, flags):
    text = ida_typeinf.print_tinfo("", 0, 0, flags, tif, name, "")
    return text if isinstance(text, str) else repr(text)


class _ProbeHooks(ida_hexrays.Hexrays_Hooks):
    def create_hint(self, vu):
        try:
            if not vu.get_current_item(ida_hexrays.USE_MOUSE):
                return 0
            summary, tif, name = describe(vu)
            lines = ["[probe] " + summary]
            if tif is not None and not tif.empty():
                for label, flags in VARIANTS:
                    text = render(tif, name, flags)
                    for i, line in enumerate(text.splitlines()):
                        lines.append((label + ": " if i == 0 else "   ") + line)
            lines.append("-" * 40)
            with open(OUT, "a", encoding="utf-8") as f:
                f.write("\n".join(repr(line) for line in lines) + "\n\n")
                f.write("\n".join(ida_lines.tag_remove(line) for line in lines) + "\n\n")
            return 0, "\n".join(lines) + "\n", len(lines)
        except Exception:
            with open(OUT, "a", encoding="utf-8") as f:
                f.write(traceback.format_exc() + "\n")
            return 0


_hooks = globals().get("_catppuccin_hint_probe")
if _hooks is not None:
    _hooks.unhook()
    globals()["_catppuccin_hint_probe"] = None
    print("hexrays hints probe: off")
else:
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, "w", encoding="utf-8").close()
    _hooks = _ProbeHooks()
    _hooks.hook()
    globals()["_catppuccin_hint_probe"] = _hooks
    print("hexrays hints probe: on (run again to turn off); logging to", OUT)
