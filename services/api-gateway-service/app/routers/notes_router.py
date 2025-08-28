# app/routers/notes_router.py
import logging
from typing import List
from fastapi import APIRouter, status, Response, HTTPException
from pydantic import BaseModel

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

class NoteOverrideRequest(BaseModel):
    new_text: str

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


@router.post(
    "/{note_id}/summarize",
    response_model=note_schemas.NoteSummaryResponse,
    tags=["AI Tools"]  # Add a new tag for organization
)
async def summarize_note(note_id: int, request: note_schemas.NoteSummaryRequest):
    """
    Generate a summary for a specific note.

    This will fetch the note's content and use the AI summary service
    to generate a summary based on the requested level of detail.
    """
    return await notes_service.generate_note_summary(
        note_id=note_id,
        summary_request=request
    )


@router.post(
    "/{note_id}/fact-check",
    response_model=note_schemas.FactCheckResponse,
    tags=["AI Tools"]
)
async def fact_check_note(note_id: int):
    """
    Fact-checks a specific note and all of its sub-notes.

    This will fetch the entire note hierarchy starting from the provided
    note_id and use the AI fact-check service to find inaccuracies.
    """
    # Using the hardcoded user ID as defined in the file
    return await notes_service.fact_check_note_and_children(
        note_id=note_id,
        user_id=HARDCODED_USER_ID
    )


@router.post(
    "/{note_id}/update-autonomous",
    response_model=note_schemas.UpdateResponse,
    tags=["AI Tools"]
)
async def update_note_autonomously(note_id: int):
    """
    Automatically finds and applies updates to a note and its children.

    The AI will analyze the content for outdated or incorrect information
    and rewrite the text with corrections.
    """
    return await notes_service.update_note_autonomously(
        note_id=note_id,
        user_id=HARDCODED_USER_ID
    )


@router.post(
    "/{note_id}/update-guided",
    response_model=note_schemas.UpdateResponse,
    tags=["AI Tools"]
)
async def update_note_with_guidance(note_id: int, request: note_schemas.GuidedUpdateRequest):
    """
    Applies a specific list of corrections to a note and its children.

    This is the ideal follow-up to a `/fact-check` call. You provide the
    corrections you want to apply, and the service rewrites the note
    content accordingly.
    """
    return await notes_service.update_note_guided(
        note_id=note_id,
        user_id=HARDCODED_USER_ID,
        request=request
    )

@router.post(
    "/{note_id}/override-content",
    status_code=status.HTTP_204_NO_CONTENT,
    tags=["Notes"] # This is a core CRUD action
)
async def override_note_content(note_id: int, request: NoteOverrideRequest):
    """
    Overrides the text content of a single note.

    This is the final step after a user approves an AI-generated update.
    The 'updated_text' from the update service is sent here to be saved.
    """
    await notes_service.override_note_content(
        note_id=note_id,
        new_text=request.new_text
    )
    return Response(status_code=status.HTTP_204_NO_CONTENT)
