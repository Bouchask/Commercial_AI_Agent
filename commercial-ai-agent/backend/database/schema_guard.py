"""Small, idempotent production-schema repairs for serverless deployments.

Alembic remains the source of truth.  This guard only covers a historic,
backwards-compatible column omission that otherwise prevents every JWT-protected
request from loading a user on Vercel, where migrations are not run at deploy.
"""
import logging

from sqlalchemy import inspect, text
from sqlalchemy.exc import SQLAlchemyError

from backend.database.connection import engine

logger = logging.getLogger(__name__)


def ensure_critical_user_columns() -> None:
    """Add authentication columns when an older users table lacks them.

    The operation is safe on concurrent serverless cold starts and never changes
    or removes existing data. Google-only accounts intentionally keep this value
    null.
    """
    try:
        inspector = inspect(engine)
        if not inspector.has_table("users"):
            return
        columns = {column["name"] for column in inspector.get_columns("users")}
        required_columns = {
            "name": "VARCHAR(255)",
            "password": "VARCHAR(255)",
            "hashed_password": "VARCHAR(255)",
            "google_id": "VARCHAR(255)",
            "google_access_token": "VARCHAR(2048)",
            "google_refresh_token": "VARCHAR(2048)",
            "default_spreadsheet_id": "VARCHAR(255)",
            "role": "VARCHAR(50) DEFAULT 'SALES'",
            "is_active": "BOOLEAN DEFAULT TRUE",
            "created_at": "TIMESTAMP WITH TIME ZONE",
            "updated_at": "TIMESTAMP WITH TIME ZONE",
        }
        missing_columns = [(name, definition) for name, definition in required_columns.items() if name not in columns]
        if not missing_columns:
            return

        with engine.begin() as connection:
            for name, definition in missing_columns:
                add_column = f"ALTER TABLE users ADD COLUMN {name} {definition}"
                if engine.dialect.name == "postgresql":
                    add_column = f"ALTER TABLE users ADD COLUMN IF NOT EXISTS {name} {definition}"
                elif "TIMESTAMP WITH TIME ZONE" in add_column:
                    add_column = add_column.replace("TIMESTAMP WITH TIME ZONE", "DATETIME")
                connection.execute(text(add_column))
            if engine.dialect.name == "postgresql":
                connection.execute(text("CREATE UNIQUE INDEX IF NOT EXISTS ix_users_google_id ON users (google_id)"))
        logger.warning("Repaired legacy users table: added authentication columns")
    except SQLAlchemyError:
        # Do not make a transient database outage prevent the function from
        # starting; health checks and the calling endpoint will report it.
        logger.exception("Could not verify the critical users-table schema")


def ensure_ownership_columns() -> None:
    """Compatibility bridge for deployments that cannot run Alembic at boot.

    New installations get this column from the Alembic migration.  The guard is
    deliberately additive only, so an existing hosted database can be upgraded
    without an outage before the normal migration job is enabled.
    """
    try:
        inspector = inspect(engine)
        if not inspector.has_table("clients"):
            return
        columns = {column["name"] for column in inspector.get_columns("clients")}
        if "owner_user_id" in columns:
            return
        statement = "ALTER TABLE clients ADD COLUMN owner_user_id INTEGER"
        if engine.dialect.name == "postgresql":
            statement = "ALTER TABLE clients ADD COLUMN IF NOT EXISTS owner_user_id INTEGER"
        with engine.begin() as connection:
            connection.execute(text(statement))
            if engine.dialect.name == "postgresql":
                connection.execute(text("CREATE INDEX IF NOT EXISTS ix_clients_owner_user_id ON clients (owner_user_id)"))
        logger.warning("Repaired legacy clients table: added owner_user_id")
    except SQLAlchemyError:
        logger.exception("Could not verify the ownership schema")
