# app/models/user.py

from __future__ import annotations # For relationship type hints
from sqlalchemy import Column, Integer, String, BigInteger, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base # Import Base from core

class AppUser(Base):
    __tablename__ = "app_user"

    id = Column(BigInteger, primary_key=True, index=True)
    version = Column(BigInteger, nullable=False)
    phone = Column(String(200), nullable=True)
    title = Column(String(255), nullable=True)
    first_name = Column(String(100), nullable=True)
    username = Column(String(255), nullable=False, unique=True, index=True) # DDL has unique constraint here
    password = Column(String(255), nullable=False) # Remember to store hashed passwords!
    last_name = Column(String(100), nullable=True)
    date_of_birth = Column(DateTime, nullable=True)
    enabled = Column(Integer, nullable=False, default=1) # Matches DDL int4 NOT NULL. Default is app-level.
    email = Column(String(255), nullable=True, index=True) # DDL does NOT enforce uniqueness here, removed unique=True

    # Relationships
    documents = relationship("Document", back_populates="owned_by")
    communications = relationship("Communication", back_populates="created_by")
    notes = relationship("Note", back_populates="owner")