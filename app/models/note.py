# app/models/note.py

from __future__ import annotations
from sqlalchemy import Column, String, BigInteger, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from app.core.database import Base
from datetime import datetime # Import for default value

class NoteType(Base):
    __tablename__ = "note_type"

    id = Column(BigInteger, primary_key=True, index=True)
    version = Column(BigInteger, nullable=False)
    name = Column(String(255), nullable=False) # DDL does NOT enforce uniqueness here, removed unique=True

    # Relationships
    notes = relationship("Note", back_populates="type")

class Note(Base):
    __tablename__ = "note"

    id = Column(BigInteger, primary_key=True, index=True)
    version = Column(BigInteger, nullable=False)
    owner_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=False, index=True) # FK matches DDL
    text = Column(String(4000), nullable=True)
    title = Column(String(255), nullable=False)
    type_id = Column(BigInteger, ForeignKey("note_type.id"), nullable=True, index=True) # FK matches DDL
    creation_date = Column(DateTime, nullable=True, default=datetime.utcnow) # Matches DDL NULL constraint. Default is app-level.
    parent_id = Column(BigInteger, ForeignKey("note.id"), nullable=True, index=True) # Self-ref FK matches DDL
    link_id = Column(BigInteger, ForeignKey("link.id"), nullable=True) # FK matches DDL
    color = Column(String(255), nullable=True)

    # Relationships
    owner = relationship("AppUser", back_populates="notes")
    type = relationship("NoteType", back_populates="notes")

    # Hierarchy relationship
    parent = relationship("Note", remote_side=[id], back_populates="children") # Correct for self-ref FK
    children = relationship("Note", back_populates="parent") # Correct for self-ref FK

    # Relationship to a specific Link via this note's link_id FK
    link = relationship("Link", foreign_keys=[link_id], back_populates="linked_notes") # Correctly uses link_id

    # Relationships to Link table where this note is the source or destination
    outgoing_links = relationship("Link", foreign_keys="Link.source_id", back_populates="source_note")
    incoming_links = relationship("Link", foreign_keys="Link.destination_id", back_populates="destination_note")

    # Relationship via association table NoteDocument
    # Ensure back_populates matches the relationship name in NoteDocument model
    documents = relationship("NoteDocument", back_populates="note")