from apps.modules.user.domain import User
from apps.modules.user.infrastructure import orm as orm_models


def build_orm(user: User) -> orm_models.User:
    """
    Конвертировать в orm-модель пользователя.

    Args:
        user: модель пользователя.

    Returns: ORM модель пользователя.

    """
    return orm_models.User(**user.to_dict())


def build(orm_user: orm_models.User) -> User:
    """
    Конвертировать из orm-модели пользователя.

    Args:
        orm_user: orm-модель пользователя.

    Returns: модель пользователя.

    """
    return User(
        uid=orm_user.uid,
        name=orm_user.name,
        password_hash=orm_user.password_hash,
        email=orm_user.email,
        created_date=orm_user.created_date,
    )
