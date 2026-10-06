"""user name and unique email

Пользователь по контракту auth.openapi.yaml (FM-15): login заменён на name (как обращаться,
не уникально), email обязателен и уникален. Пользователей в БД нет, поэтому данные не
переносятся: если найдутся пользователи без email, миграция остановится с понятной ошибкой.

Revision ID: abb6f3673f13
Revises: af1b94e3651b
Create Date: 2026-10-06 12:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "abb6f3673f13"
down_revision = "af1b94e3651b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    users_without_email = op.get_bind().scalar(sa.text("SELECT count(*) FROM users WHERE email IS NULL"))
    if users_without_email:
        msg = (
            f"В таблице users {users_without_email} пользователей без email: после FM-15 email обязателен. "
            "Заполните email или удалите этих пользователей и повторите миграцию."
        )
        raise RuntimeError(msg)

    # NOTE(FM-15): существующие email не приводятся к нижнему регистру и не проверяются на дубликаты без
    # учёта регистра, login длиннее 64 символов уронит смену типа — пользователей нет (решение в PR #11).
    op.alter_column("users", "login", new_column_name="name", type_=sa.String(length=64), existing_nullable=False)
    op.alter_column("users", "email", type_=sa.String(length=254), nullable=False, existing_nullable=True)
    op.create_unique_constraint(op.f("uq_users_email"), "users", ["email"])


def downgrade() -> None:
    op.drop_constraint(op.f("uq_users_email"), "users", type_="unique")
    op.alter_column("users", "email", type_=sa.String(), nullable=True, existing_nullable=False)
    op.alter_column("users", "name", new_column_name="login", type_=sa.String(), existing_nullable=False)
