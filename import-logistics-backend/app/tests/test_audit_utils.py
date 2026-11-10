# app/tests/test_audit_utils.py
from datetime import date
from decimal import Decimal
from enum import Enum
from types import SimpleNamespace

from app.utils.audit import REDACTED, diff, redact, snapshot, to_jsonable


class Kind(str, Enum):
    A = "a"


def test_decimals_are_stored_exactly_as_strings():
    assert to_jsonable(Decimal("12.3400")) == "12.3400"


def test_enums_and_dates_are_json_safe():
    assert to_jsonable(Kind.A) == "a"
    assert to_jsonable(date(2026, 10, 23)) == "2026-10-23"
    assert to_jsonable(None) is None


def test_snapshot_reads_only_requested_fields():
    obj = SimpleNamespace(name="x", amount=Decimal("5.5"), secret_field="no")
    assert snapshot(obj, ["name", "amount", "missing"]) == {
        "name": "x", "amount": "5.5", "missing": None,
    }


def test_diff_lists_only_changed_fields():
    before = {"amount": "100.0000", "currency": "USD", "notes": None}
    after = {"amount": "120.0000", "currency": "USD", "notes": "late fee"}
    assert diff(before, after) == {
        "amount": {"from": "100.0000", "to": "120.0000"},
        "notes": {"from": None, "to": "late fee"},
    }


def test_diff_of_identical_values_is_empty():
    assert diff({"a": 1}, {"a": 1}) == {}


def test_sensitive_values_are_redacted_at_any_depth():
    data = {"password": "hunter2", "ok": 1, "nested": {"Access_Token": "abc", "list": [{"secret": "s"}]}}
    out = redact(data)
    assert out["password"] == REDACTED
    assert out["ok"] == 1
    assert out["nested"]["Access_Token"] == REDACTED
    assert out["nested"]["list"][0]["secret"] == REDACTED
