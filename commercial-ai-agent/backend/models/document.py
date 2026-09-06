from sqlalchemy import Column, Integer, String, ForeignKey, DateTime, LargeBinary
from sqlalchemy.sql import func
from backend.models.base import Base

class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    filename = Column(String, nullable=False)
    filepath = Column(String, nullable=False)
    content = Column(LargeBinary, nullable=True) # Binary data for stateless environments
    document_type = Column(String, nullable=False) # quote, invoice, proposal
    reference_id = Column(Integer, nullable=True) # ID of the quote/invoice/proposal
    client_id = Column(Integer, ForeignKey("clients.id"), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Template(Base):
    __tablename__ = "templates"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, unique=True, index=True, nullable=False)
    document_type = Column(String, nullable=False) # quote, invoice, proposal
    filepath = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
