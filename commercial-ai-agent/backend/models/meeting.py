from sqlalchemy import Column, String, DateTime, Text
from sqlalchemy.sql import func
from backend.models.base import Base

class Meeting(Base):
    __tablename__ = "meetings"

    id = Column(String, primary_key=True, index=True)
    title = Column(String, nullable=False)
    description = Column(Text, nullable=True)
    start_time = Column(DateTime(timezone=True), nullable=False)
    end_time = Column(DateTime(timezone=True), nullable=False)
    active_from = Column(DateTime(timezone=True), nullable=True)
    active_until = Column(DateTime(timezone=True), nullable=True)
    attendees = Column(Text, nullable=True)
    google_event_id = Column(String, nullable=True)
    google_calendar_link = Column(Text, nullable=True)
    meet_url = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
