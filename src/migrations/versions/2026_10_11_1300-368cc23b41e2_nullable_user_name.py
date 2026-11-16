"""nullable user name

Имя пользователя необязательно (FM-38, contracts/auth.openapi.yaml): на экране регистрации поля имени
нет, оно задаётся в окне «Первый шаг» через PATCH /me. Существующие имена не меняются.

Revision ID: 368cc23b41e2
Revises: 667f95b5986d
Create Date: 2026-10-11 13:00:00.000000+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "368cc23b41e2"
down_revision = "667f95b5986d"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("users", "name", existing_type=sa.String(length=64), nullable=True, existing_nullable=False)


def downgrade() -> None:
    # NOTE(FM-38): до этой миграции имя обязательно, поэтому пользователям без имени подставляется часть email
    # до «@» (не длиннее 64 символов) — иначе NOT NULL не вернуть без удаления пользователей.
    op.execute(sa.text("UPDATE users SET name = left(split_part(email, '@', 1), 64) WHERE name IS NULL"))
    op.alter_column("users", "name", existing_type=sa.String(length=64), nullable=False, existing_nullable=True)
