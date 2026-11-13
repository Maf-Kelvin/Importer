from types import SimpleNamespace

from app.core.token_claims import claims_match_user, parse_subject, password_fingerprint


def user(**kw):
    base = dict(id=7, tenant_id=3, hashed_password="hash-A")
    base.update(kw)
    return SimpleNamespace(**base)


def claims(u=None, **kw):
    u = u or user()
    base = dict(sub=str(u.id), tenant_id=u.tenant_id, pwf=password_fingerprint(u.hashed_password))
    base.update(kw)
    return base


def test_valid_token_matches():
    assert claims_match_user(claims(), user())


def test_password_change_invalidates_old_tokens():
    old = claims()
    assert not claims_match_user(old, user(hashed_password="hash-B"))


def test_token_for_another_user_or_tenant_is_rejected():
    assert not claims_match_user(claims(), user(id=8))
    assert not claims_match_user(claims(), user(tenant_id=4))


def test_old_style_tokens_are_rejected():
    # issued before this change: username as subject, no pwf claim
    assert not claims_match_user({"sub": "alice", "tenant_id": 3}, user())
    assert not claims_match_user({"sub": "7", "tenant_id": 3}, user())


def test_parse_subject():
    assert parse_subject({"sub": "12"}) == 12
    assert parse_subject({"sub": "alice"}) is None
    assert parse_subject({}) is None


def test_fingerprint_is_stable_and_not_the_hash():
    assert password_fingerprint("x") == password_fingerprint("x")
    assert password_fingerprint("x") != password_fingerprint("y")
    assert "x" not in password_fingerprint("x")