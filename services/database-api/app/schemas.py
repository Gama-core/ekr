# services/database-api/app/schemas.py
import datetime
from typing import Optional
from pydantic import BaseModel, Field

# --- Pydantic API Schemas ---

class NoteForIndex(BaseModel):
    """Pydantic schema representing the data structure for a note returned by the API."""
    id: int
    title: str
    text_content: Optional[str] = Field(None, alias='text') # Use alias to map from the 'text' field of the ORM model
    owner_id: int
    creation_date: Optional[datetime.datetime]

    class Config:
        from_attributes = True # for Pydantic v2
        populate_by_name = True # Allows using 'alias'

class NoteCountResponse(BaseModel):
    """Pydantic schema for count responses."""
    count: int