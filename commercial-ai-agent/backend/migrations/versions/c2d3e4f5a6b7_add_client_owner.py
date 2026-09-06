"""add ownership boundary for commercial records

Revision ID: c2d3e4f5a6b7
Revises: 8e74d0cbd3e1
"""
from alembic import op
import sqlalchemy as sa

revision = "c2d3e4f5a6b7"
down_revision = "8e74d0cbd3e1"
branch_labels = None
depends_on = None

def upgrade():
    op.add_column("clients", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_clients_owner_user", "clients", "users", ["owner_user_id"], ["id"])
    op.create_index("ix_clients_owner_user_id", "clients", ["owner_user_id"])

def downgrade():
    op.drop_index("ix_clients_owner_user_id", table_name="clients")
    op.drop_constraint("fk_clients_owner_user", "clients", type_="foreignkey")
    op.drop_column("clients", "owner_user_id")
