# scripts/export_openapi.py
"""Write the API's OpenAPI document to a file. The frontend generates its TypeScript types from it,
so a renamed or removed field breaks the frontend BUILD instead of breaking a user.

    python scripts/export_openapi.py                       # writes ../frontend/openapi.json
    python scripts/export_openapi.py path/to/openapi.json
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from app.main import app  # noqa: E402


def main() -> int:
    target = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT.parent / "frontend" / "openapi.json"
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(app.openapi(), indent=2, sort_keys=True) + "\n")
    print(f"Wrote {target} ({len(app.openapi()['paths'])} paths)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
