# scripts/check_names.py
"""Find names that are used but never defined or imported (a NameError waiting to happen).
Standard library only (uses `symtable`). Usage: python scripts/check_names.py
"""
import builtins
import pathlib
import symtable
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
BUILTINS = set(dir(builtins)) | {"__file__", "__name__", "__doc__", "__spec__"}
problems = []


def walk(table, module_defined, rel):
    for sym in table.get_symbols():
        if table.get_type() == "function" and sym.is_global() and sym.is_referenced():
            name = sym.get_name()
            if name not in module_defined and name not in BUILTINS:
                problems.append(f"{rel}: '{name}' used in {table.get_name()}() but never defined/imported")
    for child in table.get_children():
        walk(child, module_defined, rel)


files = sorted(list((ROOT / "app").rglob("*.py")) + list((ROOT / "scripts").glob("*.py")))
for py in files:
    if "obsolete" in py.parts:
        continue
    src = py.read_text()
    top = symtable.symtable(src, str(py), "exec")
    defined = {s.get_name() for s in top.get_symbols() if s.is_assigned() or s.is_imported() or s.is_namespace()}
    # class bodies and nested scopes: names assigned in a class are not visible to methods, so only module level counts
    walk(top, defined, py.relative_to(ROOT))
    # module-level / class-level references
    for sym in top.get_symbols():
        if sym.is_referenced() and not (sym.is_assigned() or sym.is_imported() or sym.is_namespace()):
            if sym.get_name() not in BUILTINS:
                problems.append(f"{py.relative_to(ROOT)}: '{sym.get_name()}' used at module level but never defined/imported")

print(f"checked {len(files)} files")
if problems:
    print(f"{len(problems)} PROBLEM(S):")
    for p in sorted(set(problems)):
        print("  -", p)
    sys.exit(1)
print("no undefined names")
