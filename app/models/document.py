# app/models/document.py

from __future__ import annotations
from sqlalchemy import Column, String, BigInteger, ForeignKey
from sqlalchemy.orm import relationship
from app.core.database import Base

class DocumentType(Base):
    __tablename__ = "document_type"

    id = Column(BigInteger, primary_key=True, index=True)
    version = Column(BigInteger, nullable=False)
    name = Column(String(255), nullable=False) # DDL does NOT enforce uniqueness here, removed unique=True

    # Relationships
    documents = relationship("Document", back_populates="doc_type")

class Document(Base):
    __tablename__ = "document"

    id = Column(BigInteger, primary_key=True, index=True)
    doc_type_id = Column(BigInteger, ForeignKey("document_type.id"), nullable=False, index=True)
    comment = Column(String(255), nullable=True)
    mime_type = Column(String(255), nullable=True)
    owned_by_id = Column(BigInteger, ForeignKey("app_user.id"), nullable=True, index=True) # Matches DDL NULL constraint
    url = Column(String(255), nullable=True)
    path = Column(String(255), nullable=False)
    name = Column(String(255), nullable=False)

    # Relationships
    doc_type = relationship("DocumentType", back_populates="documents")
    owned_by = relationship("AppUser", back_populates="documents")
    # Relationship to Communication where this doc is the image
    communications = relationship("Communication", back_populates="image")
    # Relationship via association table NoteDocument
    notes = relationship("NoteDocument", back_populates="document", cascade="all, delete-orphan") # Relationship name updated to 'notes' for consistency if desired, check NoteDocument adjustments