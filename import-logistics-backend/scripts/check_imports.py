# scripts/check_imports.py
"""Static import checker (standard library only; no dependencies need to be installed).

For every `import app.x` / `from app.x import name` in the project it verifies that
  * the module file exists, and
  * each imported name is defined (or re-exported) by that module.
It catches the class of bug that py_compile cannot: a wrong module name or a missing
function that only explodes when the app starts.

    python scripts/check_imports.py
"""
import ast
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
APP = ROOT / "app"


def module_file(dotted: str):
    parts = dotted.split(".")
    base = ROOT.joinpath(*parts)
    if base.with_suffix(".py").is_file():
        return base.with_suffix(".py")
    if (base / "__init__.py").is_file():
        return base / "__init__.py"
    return None


_defined_cache: dict[pathlib.Path, set[str]] = {}


def defined_names(path: pathlib.Path) -> set[str]:
    if path in _defined_cache:
        return _defined_cache[path]
    names: set[str] = set()
    tree = ast.parse(path.read_text())

    def collect(body):
        for node in body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                names.add(node.name)
            elif isinstance(node, ast.Assign):
                for t in node.targets:
                    for n in ast.walk(t):
                        if isinstance(n, ast.Name):
                            names.add(n.id)
            elif isinstance(node, (ast.AnnAssign, ast.AugAssign)):
                if isinstance(node.target, ast.Name):
                    names.add(node.target.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for a in node.names:
                    names.add((a.asname or a.name).split(".")[0] if isinstance(node, ast.Import) else (a.asname or a.name))
            elif isinstance(node, (ast.If, ast.Try)):
                collect(node.body)
                collect(getattr(node, "orelse", []))
                for h in getattr(node, "handlers", []):
                    collect(h.body)
                collect(getattr(node, "finalbody", []))

    collect(tree.body)
    _defined_cache[path] = names
    return names


problems: list[str] = []
checked = 0
for py in sorted(list(APP.rglob("*.py")) + list((ROOT / "scripts").glob("*.py"))):
    if "obsolete" in py.parts:
        continue
    tree = ast.parse(py.read_text())
    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom) and node.module and node.module.split(".")[0] == "app" and node.level == 0:
            checked += 1
            target = module_file(node.module)
            rel = py.relative_to(ROOT)
            if target is None:
                problems.append(f"{rel}:{node.lineno}  module '{node.module}' does not exist")
                continue
            names = defined_names(target)
            for alias in node.names:
                if alias.name == "*":
                    continue
                sub = module_file(f"{node.module}.{alias.name}")  # importing a submodule
                if alias.name not in names and sub is None:
                    problems.append(f"{rel}:{node.lineno}  '{alias.name}' is not defined in {node.module}")
        elif isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] == "app":
                    checked += 1
                    if module_file(alias.name) is None:
                        problems.append(f"{py.relative_to(ROOT)}:{node.lineno}  module '{alias.name}' does not exist")

print(f"checked {checked} app imports")
if problems:
    print(f"{len(problems)} PROBLEM(S):")
    for p in problems:
        print("  -", p)
    sys.exit(1)
print("all app imports resolve")
