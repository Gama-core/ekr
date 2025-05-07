# app/schemas/note_document.py
# Schemas for the association table (often not directly exposed via API)

from pydantic import BaseModel
from typing import Optional

class NoteDocumentBase(BaseModel):
    # Using the correct FK names from the adjusted model
    note_id: int
    document_id: int

class NoteDocumentCreate(NoteDocumentBase):
    pass # Usually created implicitly when linking notes/docs

class NoteDocumentResponse(NoteDocumentBase):
    # Often you return the Note or Document with a list of linked items,
    # rather than the association record itself.
    pass

    class Config:
        from_attributes = True