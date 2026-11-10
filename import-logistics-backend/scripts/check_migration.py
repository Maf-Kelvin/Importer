# scripts/check_migration.py
"""Offline consistency check: do the Alembic migrations create what the models declare?

Needs NO database and NO installed packages. It
  1. reads app/models/*.py with `ast` (the expected schema), and
  2. EXECUTES every alembic/versions/*.py against stand-in `sqlalchemy` / `alembic.op` modules that
     record what the migration would create, then compares the two.

It catches: a table, column, type, nullability, foreign key, index, unique or check constraint that is
missing/different; foreign keys pointing at a table created later; duplicate or over-long (>63) names;
enum types that are never dropped on downgrade.

It is NOT a substitute for `alembic upgrade head && alembic check` against a real PostgreSQL (that is
the final authority and runs in CI), but it fails fast when a model changes without a migration.

    python scripts/check_migration.py
"""
import ast
import importlib.util
import pathlib
import sys
import types

ROOT = pathlib.Path(__file__).resolve().parent.parent
MODELS = ROOT / "app" / "models"
VERSIONS = ROOT / "alembic" / "versions"


# ============================ expected schema, from the models ============================
def _kw(call, name):
    for k in call.keywords:
        if k.arg == name:
            return k.value
    return None


def _lit(node, default=None):
    return default if node is None else ast.literal_eval(node)


def load_models():
    classes, enums = {}, {}
    for f in sorted(MODELS.glob("*.py")):
        for n in ast.parse(f.read_text()).body:
            if not isinstance(n, ast.ClassDef):
                continue
            if any("Enum" in ast.unparse(b) for b in n.bases):
                enums[n.name] = [s.targets[0].id for s in n.body
                                 if isinstance(s, ast.Assign) and isinstance(s.value, ast.Constant)]
            else:
                classes[n.name] = n
    return classes, enums


def mapped_columns(cls):
    return [(s.target.id, s.value, ast.unparse(s.annotation)) for s in cls.body
            if isinstance(s, ast.AnnAssign) and isinstance(s.target, ast.Name)
            and isinstance(s.value, ast.Call) and ast.unparse(s.value.func) == "mapped_column"]


def column_type(call, ann, enums):
    for a in call.args:
        if ast.unparse(a).startswith("ForeignKey"):
            continue
        if isinstance(a, ast.Name):
            return {"Integer": ("Integer",), "Text": ("Text",), "Boolean": ("Boolean",), "Date": ("Date",),
                    "Float": ("Float",), "JSONB": ("JSONB",), "DateTime": ("DateTime", False)}[a.id]
        fn = ast.unparse(a.func)
        if fn == "String":
            return ("String", ast.literal_eval(a.args[0]) if a.args else None)
        if fn == "Numeric":
            return ("Numeric", ast.literal_eval(a.args[0]), ast.literal_eval(a.args[1]))
        if fn == "DateTime":
            return ("DateTime", bool(_lit(_kw(a, "timezone"), False)))
        if fn == "JSONB":
            return ("JSONB",)
        if fn == "SQLEnum":
            cls = ast.unparse(a.args[0])
            return ("Enum", cls.lower(), tuple(enums[cls]))
        raise ValueError(f"unhandled type {ast.unparse(a)}")
    inner = ann.replace("Mapped[", "", 1).rstrip("]").strip()
    return {"bool": ("Boolean",), "int": ("Integer",)}[inner]


def is_nullable(call, ann):
    n = _kw(call, "nullable")
    if n is not None:
        return bool(_lit(n))
    if _lit(_kw(call, "primary_key"), False):
        return False
    return "None" in ann or "Optional" in ann


def expected_schema():
    classes, enums = load_models()
    shared = {k: mapped_columns(classes[k]) for k in ("TimestampMixin", "SoftDeleteMixin", "BaseModel")}
    parents = {"BaseModel": ("TimestampMixin", "BaseModel"), "SoftDeleteModel": ("TimestampMixin", "SoftDeleteMixin")}
    # SoftDeleteModel must define its own id (it once did not, leaving four tables without a primary key)
    shared["SoftDeleteModel"] = mapped_columns(classes["SoftDeleteModel"])
    parents["SoftDeleteModel"] = parents["SoftDeleteModel"] + ("SoftDeleteModel",)
    out = {}
    for name, cls in classes.items():
        base = next((ast.unparse(b) for b in cls.bases if ast.unparse(b) in parents), None)
        if base is None:
            continue
        table = next((s.value.value for s in cls.body if isinstance(s, ast.Assign)
                      and getattr(s.targets[0], "id", "") == "__tablename__"), name.lower())
        cols = [c for p in parents[base] for c in shared[p]] + mapped_columns(cls)
        t = {"cols": {}, "pk": set(), "fks": {}, "indexes": {}, "uniques": set(), "checks": {}}
        for cname, call, ann in cols:
            sd = _kw(call, "server_default")
            t["cols"][cname] = {"type": column_type(call, ann, enums), "nullable": is_nullable(call, ann),
                                "server_default": "now()" if sd is not None and ast.unparse(sd) == "func.now()" else None}
            if _lit(_kw(call, "primary_key"), False):
                t["pk"].add(cname)
            for a in call.args:
                if ast.unparse(a).startswith("ForeignKey"):
                    t["fks"][cname] = (ast.literal_eval(a.args[0]), _lit(_kw(a, "ondelete")))
            if _lit(_kw(call, "index"), False):
                t["indexes"][f"ix_{table}_{cname}"] = ((cname,), bool(_lit(_kw(call, "unique"), False)))
            elif _lit(_kw(call, "unique"), False):
                t["uniques"].add((cname,))
        for s in cls.body:
            if isinstance(s, ast.Assign) and getattr(s.targets[0], "id", "") == "__table_args__" \
                    and isinstance(s.value, ast.Tuple):
                for e in s.value.elts:
                    if not isinstance(e, ast.Call):
                        continue
                    fn = ast.unparse(e.func)
                    if fn == "Index":
                        t["indexes"][ast.literal_eval(e.args[0])] = (
                            tuple(ast.literal_eval(x) for x in e.args[1:]), bool(_lit(_kw(e, "unique"), False)))
                    elif fn == "UniqueConstraint":
                        t["uniques"].add(tuple(ast.literal_eval(x) for x in e.args))
                    elif fn == "CheckConstraint":
                        t["checks"][_lit(_kw(e, "name"))] = ast.literal_eval(e.args[0])
        out[table] = t
    return out, enums


# ============================ what the migrations actually create ============================
class Rec:
    def __init__(self):
        self.tables, self.order, self.indexes, self.dropped, self.sql = {}, [], {}, [], []
        self.duplicates = []   # things declared twice: PostgreSQL / SQLAlchemy reject these


def make_fakes(rec: Rec):
    class Type:
        def __init__(self, *spec):
            self.spec = spec

    def T(name):
        return lambda *a, **k: Type(name, *a)

    class Column:
        def __init__(self, name, type_, nullable=True, server_default=None, **_):
            self.name, self.type, self.nullable, self.server_default = name, type_, nullable, server_default

    class Text:
        def __init__(self, s):
            self.s = s

    sa = types.ModuleType("sqlalchemy")
    sa.Integer, sa.Text, sa.Boolean, sa.Date, sa.Float = (T(n) for n in ("Integer", "Text", "Boolean", "Date", "Float"))
    sa.String = lambda length=None: Type("String", length)
    sa.Numeric = lambda precision=None, scale=None: Type("Numeric", precision, scale)
    sa.DateTime = lambda timezone=False: Type("DateTime", bool(timezone))
    sa.Enum = lambda *labels, name=None: Type("Enum", name, tuple(labels))
    sa.Column = Column
    sa.text = Text
    sa.ForeignKeyConstraint = lambda cols, refs, ondelete=None: ("fk", tuple(cols), tuple(refs), ondelete)
    sa.PrimaryKeyConstraint = lambda *cols: ("pk", tuple(cols))
    sa.UniqueConstraint = lambda *cols, name=None: ("uq", tuple(cols), name)
    sa.CheckConstraint = lambda text, name=None: ("ck", text, name)
    pg = types.ModuleType("sqlalchemy.dialects.postgresql")
    pg.JSONB = lambda **_: Type("JSONB")
    dialects = types.ModuleType("sqlalchemy.dialects")
    dialects.postgresql = pg
    sa.dialects = dialects

    op = types.ModuleType("alembic.op")
    op.f = lambda name: name

    def create_table(name, *elements):
        rec.order.append(name)
        t = {"cols": {}, "pk": set(), "fks": {}, "uniques": set(), "checks": {}, "uq_names": []}
        if name in rec.tables:
            rec.duplicates.append(f"table '{name}' is created more than once")
        for el in elements:
            if isinstance(el, Column):
                if el.name in t["cols"]:
                    rec.duplicates.append(f"{name}: column '{el.name}' is declared more than once")
                t["cols"][el.name] = el
            elif el[0] == "pk":
                if len(set(el[1])) != len(el[1]):
                    rec.duplicates.append(f"{name}: primary key lists a column twice {el[1]}")
                t["pk"] = set(el[1])
            elif el[0] == "fk":
                t["fks"][el[1][0]] = (el[2][0], el[3])
            elif el[0] == "uq":
                t["uniques"].add(el[1]); t["uq_names"].append(el[2])
            elif el[0] == "ck":
                t["checks"][el[2]] = el[1]
        rec.tables[name] = t

    op.create_table = create_table
    def create_index(name, table, cols, unique=False, **_):
        if name in rec.indexes:
            rec.duplicates.append(f"index '{name}' is created more than once")
        rec.indexes[name] = (table, tuple(cols), bool(unique))
    op.create_index = create_index
    op.drop_table = lambda name, **_: rec.dropped.append(name)
    op.execute = lambda sql, **_: rec.sql.append(str(sql))
    op.drop_index = lambda *a, **k: None
    alembic = types.ModuleType("alembic")
    alembic.op = op
    return {"sqlalchemy": sa, "sqlalchemy.dialects": dialects, "sqlalchemy.dialects.postgresql": pg,
            "alembic": alembic, "alembic.op": op}


def run_migrations():
    files = sorted(VERSIONS.glob("*.py"))
    if not files:
        return None, "alembic/versions/ is EMPTY: there is no migration, so a clean database would get no tables"
    rec = Rec()
    saved = {k: sys.modules.get(k) for k in ("sqlalchemy", "sqlalchemy.dialects", "sqlalchemy.dialects.postgresql", "alembic", "alembic.op")}
    sys.modules.update(make_fakes(rec))
    try:
        for f in files:
            spec = importlib.util.spec_from_file_location(f"_mig_{f.stem}", f)
            mod = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(mod)
            mod.upgrade()
            up_tables = len(rec.tables)
            mod.downgrade()
        return (rec, up_tables), None
    finally:
        for k, v in saved.items():
            if v is None:
                sys.modules.pop(k, None)
            else:
                sys.modules[k] = v


# ============================ comparison ============================
def spec_of(type_obj):
    s = type_obj.spec
    if s[0] == "Enum":
        return ("Enum", s[1], s[2])
    return tuple(s)


def main() -> int:
    expected, enums = expected_schema()
    result, error = run_migrations()
    if error:
        print("FAIL:", error)
        return 1
    rec, _ = result
    problems = list(rec.duplicates)

    missing, extra = set(expected) - set(rec.tables), set(rec.tables) - set(expected)
    problems += [f"table '{t}' is in the models but no migration creates it" for t in sorted(missing)]
    problems += [f"table '{t}' is created by a migration but is not in the models" for t in sorted(extra)]

    created = set()
    for name in rec.order:
        t = rec.tables[name]
        for col, (target, _) in t["fks"].items():
            ref = target.split(".")[0]
            if ref != name and ref not in created:
                problems.append(f"{name}.{col}: foreign key to '{ref}', which is created later (or never)")
        created.add(name)

    all_names = []
    for name in sorted(set(expected) & set(rec.tables)):
        e, m = expected[name], rec.tables[name]
        if set(e["cols"]) != set(m["cols"]):
            problems.append(f"{name}: columns differ - only in models {sorted(set(e['cols']) - set(m['cols']))}, "
                            f"only in migration {sorted(set(m['cols']) - set(e['cols']))}")
        for col in sorted(set(e["cols"]) & set(m["cols"])):
            ec, mc = e["cols"][col], m["cols"][col]
            if ec["nullable"] != mc.nullable:
                problems.append(f"{name}.{col}: nullable is {mc.nullable} in the migration, {ec['nullable']} in the models")
            if tuple(ec["type"]) != spec_of(mc.type):
                problems.append(f"{name}.{col}: type {spec_of(mc.type)} in the migration, {tuple(ec['type'])} in the models")
            sd = mc.server_default.s if mc.server_default is not None else None
            if ec["server_default"] != sd:
                problems.append(f"{name}.{col}: server default {sd!r} in the migration, {ec['server_default']!r} in the models")
        if e["pk"] != m["pk"]:
            problems.append(f"{name}: primary key {sorted(m['pk'])} in the migration, {sorted(e['pk'])} in the models")
        if not e["pk"]:
            problems.append(f"{name}: the models define NO primary key (SQLAlchemy cannot map this table)")
        if e["fks"] != m["fks"]:
            problems.append(f"{name}: foreign keys differ - models {e['fks']} vs migration {m['fks']}")
        if e["uniques"] != m["uniques"]:
            problems.append(f"{name}: unique constraints differ - models {sorted(e['uniques'])} vs migration {sorted(m['uniques'])}")
        if e["checks"] != m["checks"]:
            problems.append(f"{name}: check constraints differ - models {e['checks']} vs migration {m['checks']}")
        mig_idx = {n: (cols, uq) for n, (tbl, cols, uq) in rec.indexes.items() if tbl == name}
        if e["indexes"] != mig_idx:
            problems.append(f"{name}: indexes differ - models {sorted(e['indexes'])} vs migration {sorted(mig_idx)}")
        all_names += list(mig_idx) + [n for n in m["checks"]] + [n for n in m["uq_names"] if n]

    # PostgreSQL index/constraint names live in one namespace and are limited to 63 characters
    dupes = {n for n in all_names if all_names.count(n) > 1}
    problems += [f"name '{n}' is used more than once (PostgreSQL needs unique index/constraint names)" for n in sorted(dupes)]
    problems += [f"name '{n}' is {len(n)} characters (PostgreSQL limit is 63)" for n in sorted(set(all_names)) if len(n) > 63]

    # downgrade must undo everything, including enum types
    problems += [f"downgrade does not drop table '{t}'" for t in sorted(set(rec.tables) - set(rec.dropped))]
    enum_names = sorted({c.type.spec[1] for t in rec.tables.values() for c in t["cols"].values() if c.type.spec[0] == "Enum"})
    for en in enum_names:
        if not any(f"DROP TYPE" in s and en in s for s in rec.sql):
            problems.append(f"downgrade does not drop enum type '{en}'")
    model_enum_names = {c["type"][1] for t in expected.values() for c in t["cols"].values() if c["type"][0] == "Enum"}
    if set(enum_names) != model_enum_names:
        problems.append(f"enum types differ - migration {enum_names} vs models {sorted(model_enum_names)}")

    n_cols = sum(len(t["cols"]) for t in rec.tables.values())
    print(f"models: {len(expected)} tables | migrations create: {len(rec.tables)} tables, {n_cols} columns, "
          f"{len(rec.indexes)} indexes, {len(enum_names)} enum types")
    if problems:
        print(f"{len(problems)} PROBLEM(S):")
        for p in problems:
            print("  -", p)
        return 1
    print("migrations match the models (offline check; confirm with `alembic upgrade head && alembic check`)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
