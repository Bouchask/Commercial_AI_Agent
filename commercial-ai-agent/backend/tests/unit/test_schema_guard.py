from sqlalchemy import inspect, text

from backend.database.connection import engine
from backend.database.schema_guard import ensure_critical_user_columns


def test_schema_guard_adds_missing_password_column():
    with engine.begin() as connection:
        connection.execute(text("DROP TABLE IF EXISTS users"))
        connection.execute(text("CREATE TABLE users (id INTEGER PRIMARY KEY, email VARCHAR NOT NULL)"))

    ensure_critical_user_columns()

    columns = {column["name"] for column in inspect(engine).get_columns("users")}
    assert {"name", "password", "hashed_password", "google_id", "google_access_token", "google_refresh_token", "default_spreadsheet_id", "role", "is_active", "created_at", "updated_at"} <= columns
