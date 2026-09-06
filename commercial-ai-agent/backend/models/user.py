from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.sql import func
from backend.models.base import Base

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    # Kept for compatibility with the original production users table.
    name = Column(String, nullable=True)
    email = Column(String, unique=True, index=True, nullable=False)
    # Legacy schema compatibility; password auth uses hashed_password.
    password = Column(String, nullable=True)
    hashed_password = Column(String, nullable=True)  # Nullable for Google auth users
    
    # Google OAuth fields
    google_id = Column(String, unique=True, index=True, nullable=True)
    google_access_token = Column(String, nullable=True)
    google_refresh_token = Column(String, nullable=True)
    default_spreadsheet_id = Column(String, nullable=True)
    role = Column(String, default="SALES")
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
