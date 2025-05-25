# app/db_connectors/schemas.py
from pydantic import BaseModel, Field
from typing import Optional
import datetime

class NoteForIndex(BaseModel):
    """
    Pydantic schema representing a Note's data relevant for RAG indexing.
    """
    id: int = Field(..., description="The unique ID of the note.")
    title: str = Field(..., description="The title of the note.")
    text_content: Optional[str] = Field(None, description="The main text content of the note.")
    owner_id: int = Field(..., description="The ID of the user who owns the note.")
    creation_date: Optional[datetime.datetime] = Field(None, description="When the note was created.")
    # Add any other fields from models.Note that are crucial for metadata in RAG:
    # e.g., type_name: Optional[str] = None (if you join with NoteType and want its name)
    # e.g., parent_note_id: Optional[int] = Field(None, alias="parent_id")

    class Config:
        orm_mode = True # For Pydantic v1
        # For Pydantic v2, use: from_attributes = True

# You can add other schemas here if needed for counts or other specific responses.
class NoteCountResponse(BaseModel):
    count: int