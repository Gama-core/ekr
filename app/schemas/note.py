# app/schemas/note.py

from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime

# --- Note Type Schemas ---
class NoteTypeBase(BaseModel):
    name: str = Field(..., max_length=255)

class NoteTypeCreate(NoteTypeBase):
    pass

class NoteTypeResponse(NoteTypeBase):
    id: int
    version: int

    class Config:
        from_attributes = True

# --- Note Schemas ---
class NoteBase(BaseModel):
    title: str = Field(..., max_length=255)
    text: Optional[str] = Field(None, max_length=4000) # Or remove max_length if DB is Text type
    owner_id: int # Often set from context, but needed for base ORM mapping
    type_id: Optional[int] = None
    parent_id: Optional[int] = None # For hierarchy
    link_id: Optional[int] = None
    color: Optional[str] = Field(None, max_length=7) # e.g., #RRGGBB


class NoteCreate(NoteBase):
    # Usually owner_id comes from context (logged-in user), not payload
    owner_id: Optional[int] = None # Override base to make optional in create payload
    # version is usually handled by DB/ORM, not payload
    version: Optional[int] = 0 # Provide default or remove if auto-handled

    # creation_date is usually set automatically
    creation_date: Optional[datetime] = None


class NoteResponse(NoteBase):
    id: int
    version: int
    creation_date: Optional[datetime] = None # Include if needed in response

    # Optionally include nested data:
    # owner: Optional[UserResponse] # Careful with circular deps
    # type: Optional[NoteTypeResponse]
    # children: List[NoteResponse] = [] # Be very careful with deep nesting

    class Config:
        from_attributes = True

class NoteUpdate(BaseModel):
    title: Optional[str] = Field(None, max_length=255)
    text: Optional[str] = Field(None, max_length=4000)
    owner_id: Optional[int] = None # If changing owner is allowed
    type_id: Optional[int] = None
    parent_id: Optional[int] = None
    link_id: Optional[int] = None
    color: Optional[str] = Field(None, max_length=7)

class NoteTypeUpdate(BaseModel):
    name: Optional[str] = Field(None, max_length=255)

