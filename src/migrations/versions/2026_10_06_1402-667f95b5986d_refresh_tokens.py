"""refresh tokens

Хранение refresh-токенов (FM-16): только SHA-256 открытого значения, владелец, срок действия
и признак отзыва. Токены удаляются вместе с пользователем.

Revision ID: 667f95b5986d
Revises: abb6f3673f13
Create Date: 2026-10-06 14:02:26.840116+00:00

"""

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = "667f95b5986d"
down_revision = "abb6f3673f13"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "refresh_tokens",
        sa.Column("uid", sa.UUID(), nullable=False),
        sa.Column("user_uid", sa.UUID(), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False),
        sa.Column("expires_at", sa.DateTime(), nullable=False),
        # NOTE(FM-16): значение по умолчанию есть только в ORM; вставка в обход ORM должна передавать revoked явно.
        sa.Column("revoked", sa.Boolean(), nullable=False),
        sa.Column("created_date", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["user_uid"],
            ["users.uid"],
            name=op.f("fk_refresh_tokens_user_uid_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("uid", name=op.f("pk_refresh_tokens")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_refresh_tokens_token_hash")),
    )
    op.create_index(op.f("ix_refresh_tokens_user_uid"), "refresh_tokens", ["user_uid"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_refresh_tokens_user_uid"), table_name="refresh_tokens")
    op.drop_table("refresh_tokens")
