# app/models/note_document.py
# Association table for Many-to-Many between Note and Document

from __future__ import annotations
from sqlalchemy import Column, BigInteger, ForeignKey, PrimaryKeyConstraint
from sqlalchemy.orm import relationship
from app.core.database import Base

class NoteDocument(Base):
    __tablename__ = "note_document"

    # --- Column definitions matching DDL ---
    note_documents_id = Column(BigInteger, ForeignKey("note.id"), nullable=False)
    document_id = Column(BigInteger, ForeignKey("document.id"), nullable=True) # Matches DDL nullable=True

    # --- Primary Key ---
    # Assuming a composite PK is intended for M2M, despite DDL ambiguity.
    # If note_documents_id is the *only* PK, remove __table_args__ and set primary_key=True above.
    __table_args__ = (
        PrimaryKeyConstraint('note_documents_id', 'document_id', name='note_document_pkey'), # Added optional name
    )

    # --- Relationships ---
    # Ensure back_populates matches relationship attribute names in Note and Document models
    note = relationship("Note", foreign_keys=[note_documents_id], back_populates="documents")
    document = relationship("Document", foreign_keys=[document_id], back_populates="notes") # Changed back_populates from 'notes' in Document model for clarity