# app/db_connectors/note_reader_service.py
import logging
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import func # For count operations
from typing import Optional, List, Iterator, Generator

# Assuming models.py is in the same directory or accessible via app.db_connectors
from app.db_connectors import models # SQLAlchemy models (AppUser, Note, NoteType etc.)
from app.db_connectors import schemas # Pydantic schemas (NoteForIndex)

logger = logging.getLogger(__name__)

# --- Helper to convert SQLAlchemy Note to Pydantic NoteForIndex ---
def _convert_db_note_to_schema(db_note: models.Note) -> schemas.NoteForIndex:
    """Converts a SQLAlchemy Note model instance to a NoteForIndex Pydantic schema."""
    return schemas.NoteForIndex(
        id=db_note.id,
        title=db_note.title,
        text_content=db_note.text, # Assuming 'text' is the field name in your model
        owner_id=db_note.owner_id,
        creation_date=db_note.creation_date
        # Map other fields if added to NoteForIndex
    )

# --- Service Methods ---

async def get_note_by_id_for_indexing(db: Session, note_id: int) -> Optional[schemas.NoteForIndex]:
    """
    Retrieve a single note by its ID, formatted for indexing.
    """
    logger.debug(f"Fetching note ID {note_id} for indexing.")
    # Eager load related data if needed for NoteForIndex, e.g., owner, type
    # For now, assuming NoteForIndex only needs direct fields from Note
    db_note = db.query(models.Note).filter(models.Note.id == note_id).first()

    if db_note:
        logger.info(f"Note ID {note_id} found for indexing.")
        return _convert_db_note_to_schema(db_note)
    else:
        logger.warning(f"Note ID {note_id} not found for indexing.")
        return None

async def get_all_notes_for_indexing_stream(
    db: Session, batch_size: int = 100
) -> Generator[List[schemas.NoteForIndex], None, None]:
    """
    Retrieve all notes from the database in batches, formatted for indexing.
    Yields lists of NoteForIndex.
    This uses a generator to stream results and manage memory for large datasets.
    """
    logger.info(f"Streaming all notes for indexing with batch_size {batch_size}.")
    offset = 0
    while True:
        logger.debug(f"Fetching batch of notes: offset={offset}, limit={batch_size}")
        # Similar to above, add .options(joinedload(...)) if related data is needed
        db_notes_batch = db.query(models.Note).offset(offset).limit(batch_size).all()

        if not db_notes_batch:
            logger.info("No more notes found. Streaming complete.")
            break

        notes_for_index_batch = [_convert_db_note_to_schema(note) for note in db_notes_batch]
        yield notes_for_index_batch

        if len(db_notes_batch) < batch_size:
            logger.info("Last batch fetched. Streaming complete.")
            break
        offset += batch_size
    logger.info("Finished streaming all notes for indexing.")


async def get_notes_by_user_for_indexing_stream(
    db: Session, owner_id: int, batch_size: int = 100
) -> Generator[List[schemas.NoteForIndex], None, None]:
    """
    Retrieve all notes for a specific user in batches, formatted for indexing.
    Yields lists of NoteForIndex.
    """
    logger.info(f"Streaming notes for owner_id {owner_id} for indexing with batch_size {batch_size}.")
    offset = 0
    while True:
        logger.debug(f"Fetching batch of notes for owner {owner_id}: offset={offset}, limit={batch_size}")
        db_notes_batch = (
            db.query(models.Note)
            .filter(models.Note.owner_id == owner_id)
            .offset(offset)
            .limit(batch_size)
            .all()
        )

        if not db_notes_batch:
            logger.info(f"No more notes found for owner {owner_id}. Streaming complete.")
            break

        notes_for_index_batch = [_convert_db_note_to_schema(note) for note in db_notes_batch]
        yield notes_for_index_batch

        if len(db_notes_batch) < batch_size:
            logger.info(f"Last batch fetched for owner {owner_id}. Streaming complete.")
            break
        offset += batch_size
    logger.info(f"Finished streaming notes for owner_id {owner_id} for indexing.")

async def get_all_notes_count(db: Session) -> int:
    """
    Get the total count of all notes in the database.
    """
    logger.debug("Counting all notes.")
    count = db.query(func.count(models.Note.id)).scalar()
    logger.info(f"Total notes count: {count}")
    return count or 0

async def get_notes_by_user_count(db: Session, owner_id: int) -> int:
    """
    Get the total count of notes for a specific user.
    """
    logger.debug(f"Counting notes for owner_id {owner_id}.")
    count = (
        db.query(func.count(models.Note.id))
        .filter(models.Note.owner_id == owner_id)
        .scalar()
    )
    logger.info(f"Notes count for owner_id {owner_id}: {count}")
    return count or 0