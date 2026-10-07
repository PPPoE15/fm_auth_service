from datetime import UTC, datetime, timedelta
from uuid import uuid4

from apps.web.app.aggregators.models import RefreshToken

NOW = datetime(2026, 10, 7, 12, 0, tzinfo=UTC)


def _token(expires_at: datetime = NOW + timedelta(days=1), *, revoked: bool = False) -> RefreshToken:
    token = RefreshToken.create(user_uid=uuid4(), token_hash="hash", expires_at=expires_at, created_date=NOW)
    if revoked:
        token.revoke()
    return token


def test_new_token_is_active() -> None:
    assert _token().is_active(NOW) is True


def test_revoked_token_is_not_active() -> None:
    assert _token(revoked=True).is_active(NOW) is False


def test_expired_token_is_not_active() -> None:
    assert _token(expires_at=NOW - timedelta(seconds=1)).is_active(NOW) is False


def test_token_is_not_active_at_the_moment_of_expiry() -> None:
    assert _token(expires_at=NOW).is_active(NOW) is False


def test_revoke_marks_token_revoked() -> None:
    token = _token()

    token.revoke()

    assert token.revoked is True


def test_revoke_is_idempotent() -> None:
    token = _token(revoked=True)

    token.revoke()

    assert token.revoked is True


def test_token_belongs_only_to_its_user() -> None:
    token = _token()

    assert token.belongs_to(token.user_uid) is True
    assert token.belongs_to(uuid4()) is False
