# services/database-api/app/endpoints.py
import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from fastapi.responses import StreamingResponse

# Use relative imports
from . import service
from .schemas import NoteForIndex, NoteCountResponse
from .database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

@router.get("/notes/{note_id}", response_model=NoteForIndex, tags=["Notes"])
async def get_note_endpoint(note_id: int, db: Session = Depends(get_db)):
    # ... (implementation is identical) ...
    logger.info(f"API: Request for note_id: {note_id}")
    note_orm = await service.get_note_by_id(db, note_id)
    if not note_orm:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")
    return NoteForIndex.model_validate(note_orm)

@router.get("/notes/stream/all", tags=["Notes"])
async def stream_all_notes_endpoint(db: Session = Depends(get_db)):
    """Streams all notes as newline-delimited JSON."""
    async def stream_generator():
        async for notes_batch in service.get_all_notes_stream(db):
            for note in notes_batch:
                pydantic_note = NoteForIndex.model_validate(note)
                yield pydantic_note.model_dump_json() + "\n"
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

@router.get("/notes/stream/by-user/{user_id}", tags=["Notes"])
async def stream_notes_by_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Streams all notes for a specific user as newline-delimited JSON."""
    async def stream_generator():
        async for notes_batch in service.get_notes_by_user_stream(db, owner_id=user_id):
            for note in notes_batch:
                pydantic_note = NoteForIndex.model_validate(note)
                yield pydantic_note.model_dump_json() + "\n"
    return StreamingResponse(stream_generator(), media_type="application/x-ndjson")

@router.get("/notes/count/all", response_model=NoteCountResponse, tags=["Notes"])
async def get_total_note_count_endpoint(db: Session = Depends(get_db)):
    """Get the total count of all notes."""
    count = await service.get_all_notes_count(db)
    return NoteCountResponse(count=count)

@router.get("/notes/count/by-user/{user_id}", response_model=NoteCountResponse, tags=["Notes"])
async def get_note_count_by_user_endpoint(user_id: int, db: Session = Depends(get_db)):
    """Get the total count of notes for a specific user."""
    count = await service.get_notes_by_user_count(db, owner_id=user_id)
    return NoteCountResponse(count=count)