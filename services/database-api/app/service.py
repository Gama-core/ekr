# services/database-api/app/service.py
import logging
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Generator, List

from .database import Note

logger = logging.getLogger(__name__)

async def get_note_by_id(db: Session, note_id: int) -> Optional[Note]:
    """Retrieve a single note by its ID from the database."""
    logger.debug(f"Fetching note ID {note_id} from DB.")
    return db.query(Note).filter(Note.id == note_id).first()

async def get_all_notes_stream(db: Session, batch_size: int = 100) -> Generator[List[Note], None, None]:
    """Generator function to stream all notes from the database in batches."""
    logger.info(f"Streaming all notes with batch_size {batch_size}.")
    offset = 0
    while True:
        db_notes_batch = db.query(Note).offset(offset).limit(batch_size).all()
        if not db_notes_batch:
            break
        yield db_notes_batch
        if len(db_notes_batch) < batch_size:
            break
        offset += batch_size
    logger.info("Finished streaming all notes.")

async def get_notes_by_user_stream(db: Session, owner_id: int, batch_size: int = 100) -> Generator[List[Note], None, None]:
    """Generator to stream all notes for a specific user in batches."""
    logger.info(f"Streaming notes for owner_id {owner_id} with batch_size {batch_size}.")
    offset = 0
    while True:
        db_notes_batch = db.query(Note).filter(Note.owner_id == owner_id).offset(offset).limit(batch_size).all()
        if not db_notes_batch:
            break
        yield db_notes_batch
        if len(db_notes_batch) < batch_size:
            break
        offset += batch_size
    logger.info(f"Finished streaming notes for owner_id {owner_id}.")

async def get_all_notes_count(db: Session) -> int:
    """Get the total count of all notes."""
    count = db.query(func.count(Note.id)).scalar()
    return count or 0

async def get_notes_by_user_count(db: Session, owner_id: int) -> int:
    """Get the total count of notes for a specific user."""
    count = db.query(func.count(Note.id)).filter(Note.owner_id == owner_id).scalar()
    return count or 0