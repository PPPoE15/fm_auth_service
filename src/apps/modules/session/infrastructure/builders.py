from apps.modules.session.domain import RefreshToken
from apps.modules.session.infrastructure import orm as orm_models


def build_orm(refresh_token: RefreshToken) -> orm_models.RefreshToken:
    """
    Конвертировать в orm-модель refresh-токена.

    Args:
        refresh_token: модель refresh-токена.

    Returns: ORM модель refresh-токена.

    """
    return orm_models.RefreshToken(**refresh_token.to_dict())


def build(orm_refresh_token: orm_models.RefreshToken) -> RefreshToken:
    """
    Конвертировать из orm-модели refresh-токена.

    Args:
        orm_refresh_token: orm-модель refresh-токена.

    Returns: модель refresh-токена.

    """
    return RefreshToken(
        uid=orm_refresh_token.uid,
        user_uid=orm_refresh_token.user_uid,
        token_hash=orm_refresh_token.token_hash,
        expires_at=orm_refresh_token.expires_at,
        revoked=orm_refresh_token.revoked,
        created_date=orm_refresh_token.created_date,
    )
