from sqlalchemy import Column, Integer, String, DateTime, JSON, Float
from sqlalchemy.sql import func
from backend.models.base import Base

class Execution(Base):
    __tablename__ = "executions"

    id = Column(String, primary_key=True, index=True) # UUID string
    session_id = Column(String, index=True, nullable=True)
    user_id = Column(Integer, nullable=True)
    title = Column(String, nullable=True) # Intelligent title
    state = Column(String, default="RECEIVED")
    result_summary = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

class Message(Base):
    __tablename__ = "messages"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False) # 'user' or 'agent'
    content = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ToolCall(Base):
    __tablename__ = "tool_calls"

    id = Column(Integer, primary_key=True, index=True)
    execution_id = Column(String, index=True, nullable=False)
    tool_name = Column(String, nullable=False)
    arguments = Column(JSON, nullable=True)
    status = Column(String, nullable=False) # SUCCESS, FAILED, WAITING_APPROVAL
    duration = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
