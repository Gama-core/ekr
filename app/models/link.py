# app/models/link.py

from __future__ import annotations
from sqlalchemy import Column, String, BigInteger, ForeignKey, Boolean
from sqlalchemy.orm import relationship
from app.core.database import Base

class Link(Base):
    __tablename__ = "link"

    id = Column(BigInteger, primary_key=True, index=True)
    version = Column(BigInteger, nullable=False)
    link_type = Column(String(255), nullable=True)
    destination_id = Column(BigInteger, ForeignKey("note.id"), nullable=True, index=True) # FK matches DDL
    source_id = Column(BigInteger, ForeignKey("note.id"), nullable=True, index=True)      # FK matches DDL
    url = Column(String(255), nullable=True)
    is_web_link = Column(Boolean, nullable=True, default=False) # Matches DDL NULL constraint. Default is app-level.

    # Relationships
    source_note = relationship("Note", foreign_keys=[source_id], back_populates="outgoing_links")
    destination_note = relationship("Note", foreign_keys=[destination_id], back_populates="incoming_links")
    # Relationship to Note via Note.link_id FK
    linked_notes = relationship("Note", foreign_keys="Note.link_id", back_populates="link")