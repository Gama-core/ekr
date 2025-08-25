# app/schemas/note_schemas.py
import datetime
from typing import Optional, List
from pydantic import BaseModel, Field

# Schema for the request body when CREATING a note
class NoteCreateRequest(BaseModel):
    title: str = Field(..., min_length=1)
    text: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None

# Schema for the request body when UPDATING a note
class NoteUpdateRequest(BaseModel):
    title: Optional[str] = Field(None, min_length=1)
    text: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None

# Schema for the response body when returning a note
class NoteResponse(BaseModel):
    id: int
    owner_id: int
    title: str
    text: Optional[str] = None
    parent_id: Optional[int] = None
    color: Optional[str] = None
    creation_date: Optional[datetime.datetime] = None
    version: int

    class Config:
        from_attributes = True