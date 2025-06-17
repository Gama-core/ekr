# app/features/elasticsearch/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class TicketRequest(BaseModel):
    note_id: int = Field(..., description="The ID of the note to index into Elasticsearch.")

    model_config = {
        "json_schema_extra": { "examples": [{ "note_id": 42 }] }
    }

# --- ADD THIS NEW SCHEMA ---
class NoteForIndex(BaseModel):
    """Schema for a note fetched from the database-api, ready for indexing."""
    id: int
    title: Optional[str] = None
    text: Optional[str] = None
    color: Optional[str] = None
    owner_id: Optional[int] = None
    type_id: Optional[int] = None
    creation_date: Optional[datetime] = None
    parent_id: Optional[int] = None
    link_id: Optional[int] = None

class NoteSearchHit(BaseModel):
    note_id: int = Field(..., description="Unique ID of the note.")
    title: Optional[str] = Field(None, description="Title of the note.")
    text: Optional[str] = Field(None, description="Main content of the note.")
    color: Optional[str] = Field(None, description="Optional color label.")
    owner_id: Optional[int] = Field(None, description="User ID of the note's owner.")
    type_id: Optional[int] = Field(None, description="Note type identifier.")
    creation_date: Optional[str] = Field(None, description="ISO formatted creation date.")
    parent_note_id: Optional[int] = Field(None, description="Parent note ID (if it's a sub-note).")
    link_id: Optional[int] = Field(None, description="Optional link ID to related entities.")

    model_config = {
        "json_schema_extra": {
            "examples": [{
                "note_id": 42,
                "title": "Meeting Notes",
                "text": "Discussed quarterly goals and deliverables.",
                "color": "blue",
                "owner_id": 3,
                "type_id": 1,
                "creation_date": "2024-05-26T10:15:30",
                "parent_note_id": None,
                "link_id": 7
            }]
        }
    }


class ReindexResponse(BaseModel):
    message: str = Field(..., description="Human-readable message about the indexing result.")
    status: bool = Field(..., description="Indicates whether the operation was successful.")


class DeleteResponse(BaseModel):
    message: str = Field(..., description="Result of deletion from Elasticsearch.")