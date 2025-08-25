# services/database-api/app/schemas.py

import datetime
from typing import Optional
from pydantic import BaseModel, Field

# --- NEW: Base schema with common fields for creating/updating ---
class NoteBase(BaseModel):
    title: str = Field(min_length=1)
    text_content: Optional[str] = Field(None, alias='text')
    parent_id: Optional[int] = None
    color: Optional[str] = None

    class Config:
        populate_by_name = True # Allows using 'alias'

# --- NEW: Schema for creating a note (requires owner_id) ---
class NoteCreate(NoteBase):
    owner_id: int

# --- NEW: Schema for updating a note (all fields are optional) ---
class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    text_content: Optional[str] = Field(None, alias='text')
    parent_id: Optional[int] = None
    color: Optional[str] = None

# --- NEW: Full Note schema for API responses ---
class Note(BaseModel):
    id: int
    version: int
    owner_id: int
    title: str
    text_content: Optional[str] = Field(alias='text')
    type_id: Optional[int] = None
    creation_date: Optional[datetime.datetime] = None
    parent_id: Optional[int] = None
    link_id: Optional[int] = None
    color: Optional[str] = None

    class Config:
        from_attributes = True
        populate_by_name = True

# --- EXISTING: Schema for indexing, still useful for RAG ---
class NoteForIndex(BaseModel):
    id: int
    title: str
    text_content: Optional[str] = Field(None, alias='text')
    owner_id: int
    creation_date: Optional[datetime.datetime]

    class Config:
        from_attributes = True
        populate_by_name = True

class NoteCountResponse(BaseModel):
    count: int