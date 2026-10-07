"""Bundle a Python entry point and the local modules it imports into one
source file.

Local modules are .py files under the entry point's folder, named from it
(`perf` is perf.py, `ida.chrome` is ida/chrome.py). Every local module the
entry point imports, directly or indirectly, is inlined above it in
dependency order; imports of local modules are dropped and all other
top-level imports are hoisted to the top.

Rules for the modules, so the flattened file behaves like the modules did:
- import local modules as `from module import name` (`from ida.chrome import
  Chrome`), never `import module` or `from package import module`
- top-level names must be unique across all bundled modules
"""

import ast
import io
import tokenize
from typing import Callable, NamedTuple, Optional

from common.errors import ScriptError
from common.paths import rel


class Guard(NamedTuple):
    """Only run the bundle when `condition` holds; otherwise run `fallback`.
    The bundle's imports and modules go inside `if condition:`, so nothing
    they import is loaded when it does not hold (e.g. a module that refuses
    to import there)."""
    imports: str            # statements the condition and fallback need, placed before it
    condition: str          # a Python expression
    fallback: str           # statements for the `else:` branch


def _indent(source, prefix="    "):
    """`source` indented one level, except the lines inside multi-line
    strings (their content must not change; Python does not care about their
    indentation)."""
    inside = set()               # 1-based line numbers continuing a multi-line token
    for token in tokenize.generate_tokens(io.StringIO(source).readline):
        if token.end[0] > token.start[0]:
            inside.update(range(token.start[0] + 1, token.end[0] + 1))
    return "\n".join(prefix + line if line.strip() and number not in inside else line
                     for number, line in enumerate(source.split("\n"), 1))


class Bundle(NamedTuple):
    source: str     # the bundled file's text
    modules: list   # paths of the bundled modules, in the order they appear


def _defined_names(tree):
    names = set()
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            names.add(node.name)
        elif isinstance(node, (ast.Assign, ast.AnnAssign)):
            targets = node.targets if isinstance(node, ast.Assign) else [node.target]
            for t in targets:
                for n in ast.walk(t):
                    if isinstance(n, ast.Name):
                        names.add(n.id)
    return names


class _Module:
    def __init__(self, path, is_local, is_package, missing_hint):
        self.path = path
        self.source = path.read_text(encoding="utf-8")
        self.lines = self.source.splitlines()
        self.tree = ast.parse(self.source, str(path))
        self.defined = _defined_names(self.tree)
        self.deps = []            # local modules, in import order
        self.imports = []         # external import statements (source text)
        self.local_imports = []   # (module, [names], lineno)
        self.drop = set()         # 0-based line numbers to leave out
        self.docstring = None     # source text, copied verbatim

        where = rel(path)
        body = self.tree.body
        if ast.get_docstring(self.tree) is not None:
            self.docstring = self._text(body[0])
            self._drop(body[0])
        for node in body:
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if is_local(alias.name):
                        raise ScriptError(
                            "%s:%d: use `from %s import ...`, not `import %s`"
                            % (where, node.lineno, alias.name, alias.name))
                self.imports.append(self._text(node))
                self._drop(node)
            elif isinstance(node, ast.ImportFrom):
                local = node.level == 0 and is_local(node.module)
                if node.level == 0 and is_package(node.module):
                    raise ScriptError("%s:%d: import names from a module, not modules from `%s`"
                                      % (where, node.lineno, node.module))
                if node.level == 0 and node.module and not local:
                    hint = missing_hint(node.module)
                    if hint:
                        raise ScriptError("%s:%d: %s" % (where, node.lineno, hint))
                if local:
                    names = [a.name for a in node.names]
                    if "*" in names or any(a.asname for a in node.names):
                        raise ScriptError("%s:%d: no `*` or `as` when importing local modules"
                                          % (where, node.lineno))
                    self.deps.append(node.module)
                    self.local_imports.append((node.module, names, node.lineno))
                else:
                    self.imports.append(self._text(node))
                self._drop(node)

    def _drop(self, node):
        self.drop.update(range(node.lineno - 1, node.end_lineno))

    def _text(self, node):
        return "\n".join(self.lines[node.lineno - 1:node.end_lineno])

    def body(self):
        kept = [l for i, l in enumerate(self.lines) if i not in self.drop]
        return "\n".join(kept).strip("\n")


def bundle_python_modules(entry_point, header="",
                          missing_hint: Callable[[str], Optional[str]] = lambda name: None,
                          guard: Optional[Guard] = None):
    """Bundle `entry_point` (a .py file) with the local modules it imports.

    `header` is a comment placed after the entry point's docstring.
    `guard` (a Guard) wraps the bundle in a condition.
    `missing_hint(module)` is asked about every `from module import ...` that
    is not a local module; it returns an error message to fail with (e.g.
    for a generated module that is not built yet), or None for an external
    import."""
    folder = entry_point.parent

    def module_path(name):
        return folder.joinpath(*name.split(".")).with_suffix(".py")

    def is_local(name):
        return name is not None and module_path(name).is_file()

    def is_package(name):
        return name is not None and folder.joinpath(*name.split(".")).is_dir()

    entry = entry_point.stem
    modules, order = {}, []

    def collect(name, visiting):
        if name in modules:
            return
        if name in visiting:
            raise ScriptError("import cycle through %s" % rel(module_path(name)))
        visiting.add(name)
        mod = _Module(entry_point if name == entry else module_path(name), is_local, is_package,
                      missing_hint)
        for dep in mod.deps:
            collect(dep, visiting)
        visiting.discard(name)
        modules[name] = mod
        order.append(name)

    collect(entry, set())

    # every name imported from a local module must exist there
    for mod in modules.values():
        for dep, names, lineno in mod.local_imports:
            missing = [n for n in names if n not in modules[dep].defined]
            if missing:
                raise ScriptError("%s:%d: %s not defined at top level of %s"
                                  % (rel(mod.path), lineno, ", ".join(missing), rel(modules[dep].path)))

    # top-level names share one namespace once flattened
    owner = {}
    for name in order:
        for n in modules[name].defined:
            if n in owner:
                raise ScriptError("`%s` is defined in both %s and %s"
                                  % (n, rel(modules[owner[n]].path), rel(modules[name].path)))
            owner[n] = name

    imports = []
    for name in order:
        for imp in modules[name].imports:
            if imp not in imports:
                imports.append(imp)
    imports.sort(key=lambda s: not s.startswith("from __future__"))

    parts = []
    if modules[entry].docstring is not None:
        parts.append(modules[entry].docstring)
    if header:
        parts.append(header)
    body = ["\n".join(imports)]
    for name in order:
        body.append("# " + "-" * 68 + "\n# %s\n# " % rel(modules[name].path) + "-" * 68
                    + "\n\n" + modules[name].body())
    if guard is None:
        parts += body
    else:
        parts.append(guard.imports.strip("\n"))
        parts.append("if %s:\n%s\nelse:\n%s" % (
            guard.condition, _indent("\n\n\n".join(body)), _indent(guard.fallback.strip("\n"))))
    source = "\n\n\n".join(parts) + "\n"
    compile(source, str(entry_point), "exec")
    return Bundle(source, [modules[name].path for name in order])
