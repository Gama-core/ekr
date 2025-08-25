# app/routers/notes_router.py
import logging
from typing import List
from fastapi import APIRouter, status, Response, HTTPException

from ..services import notes_service
from ..schemas import note_schemas

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/notes",
    tags=["Notes"]
)

# For now, we hardcode the user_id to 1 as per our security requirement.
# In a real app, this would come from an authentication token.
HARDCODED_USER_ID = 1

@router.get("/{note_id}", response_model=note_schemas.NoteResponse)
async def get_note_by_id(note_id: int):
    """Get a single note by its ID."""
    note = await notes_service.get_note_by_id(note_id=note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note

@router.get("", response_model=List[note_schemas.NoteResponse])
async def get_notes_for_user():
    """Get all notes for the authenticated user."""
    return await notes_service.get_all_notes(user_id=HARDCODED_USER_ID)

@router.post("", response_model=note_schemas.NoteResponse, status_code=status.HTTP_201_CREATED)
async def create_note(note: note_schemas.NoteCreateRequest):
    """Create a new note for the authenticated user."""
    return await notes_service.create_new_note(note_create=note, user_id=HARDCODED_USER_ID)

@router.put("/{note_id}", response_model=note_schemas.NoteResponse)
async def update_note(note_id: int, note: note_schemas.NoteUpdateRequest):
    """Update an existing note."""
    return await notes_service.update_existing_note(note_id=note_id, note_update=note)

@router.delete("/{note_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_note(note_id: int):
    """Delete an existing note."""
    await notes_service.delete_existing_note(note_id=note_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)