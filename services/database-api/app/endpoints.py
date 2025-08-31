# services/database-api/app/endpoints.py

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse
from typing import List # --- NEW: Import List ---

# Use relative imports and add new schemas
from . import service, schemas
from .database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

# Endpoint to create a note
@router.post("/notes", response_model=schemas.Note, status_code=status.HTTP_201_CREATED, tags=["Notes CRUD"])
async def create_note_endpoint(note: schemas.NoteCreate, db: Session = Depends(get_db)):
    """Creates a new note in the database."""
    return await service.create_note(db=db, note=note)

# Changed path and response_model for clarity
@router.get("/notes/by-id/{note_id}", response_model=schemas.Note, tags=["Notes Read-Only"])
async def get_note_endpoint(note_id: int, db: Session = Depends(get_db)):
    """Retrieves a single note by its ID."""
    logger.info(f"API: Request for note_id: {note_id}")
    note_orm = await service.get_note_by_id(db, note_id)
    if not note_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return note_orm

# --- NEW ENDPOINT TO BE ADDED ---
@router.get("/notes/by-user/{user_id}", response_model=List[schemas.Note], tags=["Notes Read-Only"])
async def get_notes_by_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Retrieves all notes for a specific user as a single JSON list."""
    return await service.get_notes_by_user(db, owner_id=user_id)
# --- END OF NEW ENDPOINT ---


# Endpoint to update a note
@router.put("/notes/{note_id}", response_model=schemas.Note, tags=["Notes CRUD"])
async def update_note_endpoint(note_id: int, note_update: schemas.NoteUpdate, db: Session = Depends(get_db)):
    """Updates an existing note."""
    updated_note = await service.update_note(db, note_id, note_update)
    if not updated_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return updated_note

# Endpoint to delete a note
@router.delete("/notes/{note_id}", response_model=schemas.Note, tags=["Notes CRUD"])
async def delete_note_endpoint(note_id: int, db: Session = Depends(get_db)):
    """Deletes a note from the database."""
    deleted_note = await service.delete_note(db, note_id)
    if not deleted_note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return deleted_note


# --- CORRECTED STREAMING ENDPOINTS START HERE ---

@router.get("/notes/stream/all", tags=["Notes Read-Only"])
async def stream_all_notes_endpoint(db: Session = Depends(get_db)):
    """Streams all notes as newline-delimited JSON."""
    async def stream_generator():
        async for notes_batch in service.get_all_notes_stream(db):
            for note in notes_batch:
                # FIX: Use the full 'Note' schema to include the 'version' field
                pydantic_note = schemas.Note.model_validate(note)
                yield pydantic_note.model_dump_json(by_alias=True) + "\n"
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

@router.get("/notes/stream/by-user/{user_id}", tags=["Notes Read-Only"])
async def stream_notes_by_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Streams all notes for a specific user as newline-delimited JSON."""
    async def stream_generator():
        async for notes_batch in service.get_notes_by_user_stream(db, owner_id=user_id):
            for note in notes_batch:
                # FIX: Use the full 'Note' schema to include the 'version' field
                pydantic_note = schemas.Note.model_validate(note)
                yield pydantic_note.model_dump_json(by_alias=True) + "\n"
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

# --- CORRECTED STREAMING ENDPOINTS END HERE ---


@router.get("/notes/count/all", response_model=schemas.NoteCountResponse, tags=["Notes Read-Only"])
async def get_total_note_count_endpoint(db: Session = Depends(get_db)):
    """Get the total count of all notes."""
    count = await service.get_all_notes_count(db)
    return schemas.NoteCountResponse(count=count)

@router.get("/notes/count/by-user/{user_id}", response_model=schemas.NoteCountResponse, tags=["Notes Read-Only"])
async def get_note_count_by_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Get the total count of notes for a specific user."""
    count = await service.get_notes_by_user_count(db, owner_id=user_id)
    return schemas.NoteCountResponse(count=count)