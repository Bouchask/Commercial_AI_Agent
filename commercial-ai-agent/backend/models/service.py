from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from backend.models.base import Base

class Category(Base):
    __tablename__ = "service_categories"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    
    services = relationship("Service", back_populates="category")

class Catalogue(Base):
    __tablename__ = "catalogues"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, index=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    services = relationship("Service", back_populates="catalogue")

class Service(Base):
    __tablename__ = "services"

    id = Column(Integer, primary_key=True, index=True)
    code = Column(String, unique=True, index=True, nullable=False)
    name = Column(String, index=True, nullable=False)
    description = Column(String, nullable=True)
    unit = Column(String, default="unit")
    unit_price = Column(Float, nullable=False)
    currency = Column(String, default="MAD")
    tax_rate = Column(Float, default=0.20)
    
    category_id = Column(Integer, ForeignKey("service_categories.id"), nullable=True)
    catalogue_id = Column(Integer, ForeignKey("catalogues.id"), nullable=True)

    category = relationship("Category", back_populates="services")
    catalogue = relationship("Catalogue", back_populates="services")
