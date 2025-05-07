# app/models/communication.py

from __future__ import annotations
from sqlalchemy import Column, String, BigInteger, ForeignKey, DateTime, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime

class Communication(Base):
    __tablename__ = "communication"

    id = Column(BigInteger, primary_key=True, index=True)
    version = Column(BigInteger, nullable=False)
    title = Column(String(255), nullable=False)
    publication_start_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    publication_end_date = Column(DateTime, nullable=True)
    image_id = Column(BigInteger, ForeignKey("document.id"), nullable=True) # Link to an image document
    creation_date = Column(DateTime, nullable=False, default=datetime.utcnow)
    created_by_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=False, index=True)
    external = Column(Boolean, nullable=True, default=False) # Is this for external audience?
    text = Column(String(255), nullable=False) # Should this be longer? Use Text?

    # Relationships
    image = relationship("Document", back_populates="communications")
    created_by = relationship("AppUser", back_populates="communications")