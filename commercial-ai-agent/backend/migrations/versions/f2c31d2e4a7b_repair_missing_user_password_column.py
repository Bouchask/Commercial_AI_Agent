"""Repair historic deployments missing user authentication columns.

Revision ID: f2c31d2e4a7b
Revises: 8e74d0cbd3e1
Create Date: 2026-09-01
"""
from alembic import op
import sqlalchemy as sa


revision = "f2c31d2e4a7b"
down_revision = "8e74d0cbd3e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()
    columns = {column["name"] for column in sa.inspect(bind).get_columns("users")}
    required_columns = {
        "name": sa.String(length=255),
        "password": sa.String(length=255),
        "hashed_password": sa.String(length=255),
        "google_id": sa.String(length=255),
        "google_access_token": sa.String(length=2048),
        "google_refresh_token": sa.String(length=2048),
        "default_spreadsheet_id": sa.String(length=255),
        "role": sa.String(length=50),
        "is_active": sa.Boolean(),
        "created_at": sa.DateTime(timezone=True),
        "updated_at": sa.DateTime(timezone=True),
    }
    for name, column_type in required_columns.items():
        if name not in columns:
            op.add_column("users", sa.Column(name, column_type, nullable=True))
    indexes = {index["name"] for index in sa.inspect(bind).get_indexes("users")}
    if "ix_users_google_id" not in indexes:
        op.create_index("ix_users_google_id", "users", ["google_id"], unique=True)


def downgrade() -> None:
    # The column may hold credentials created after this migration. Do not
    # delete it automatically in a downgrade.
    pass
