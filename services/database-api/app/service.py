# services/database-api/app/service.py

import logging
import datetime
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Optional, Generator, List
from fastapi import HTTPException, status # --- NEW: Import HTTPException ---

# --- MODIFIED: Import models and schemas ---
from . import models, schemas

logger = logging.getLogger(__name__)


# --- NEW: HELPER FUNCTION FOR RECURSIVE DELETION ---
def _get_all_descendant_ids(db: Session, note_id: int) -> List[int]:
    """
    Recursively finds all descendant note IDs for a given note.
    """
    descendant_ids = []
    # Find direct children
    children = db.query(models.Note.id).filter(models.Note.parent_id == note_id).all()

    for child_id_tuple in children:
        child_id = child_id_tuple[0]
        descendant_ids.append(child_id)
        # Recursively find grandchildren
        descendant_ids.extend(_get_all_descendant_ids(db, child_id))

    return descendant_ids


# --- Service functions for read operations ---
async def get_note_by_id(db: Session, note_id: int) -> Optional[models.Note]:
    """Retrieve a single note by its ID from the database."""
    logger.debug(f"Fetching note ID {note_id} from DB.")
    return db.query(models.Note).filter(models.Note.id == note_id).first()


async def get_notes_by_user(db: Session, owner_id: int) -> List[models.Note]:
    """Retrieve all notes for a single user from the database in one query."""
    logger.info(f"Fetching all notes for owner_id {owner_id}.")
    return db.query(models.Note).filter(models.Note.owner_id == owner_id).all()


# --- Service functions for write operations ---
async def create_note(db: Session, note: schemas.NoteCreate) -> models.Note:
    """Create a new note in the database."""
    if note.owner_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only user_id=1 can create notes."
        )
    logger.info(f"Creating note for owner_id: {note.owner_id} with title: '{note.title}'")
    db_note = models.Note(
        **note.model_dump(exclude={'text_content'}),
        text=note.text_content,
        version=1,
        creation_date=datetime.datetime.utcnow()
    )
    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note


async def update_note(db: Session, note_id: int, note_update: schemas.NoteUpdate) -> Optional[models.Note]:
    """Update an existing note in the database."""
    db_note = await get_note_by_id(db, note_id)
    if not db_note: return None

    if db_note.owner_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only notes owned by user_id=1 can be updated."
        )
    logger.info(f"Updating note ID: {note_id}")
    update_data = note_update.model_dump(exclude_unset=True, by_alias=True)
    for key, value in update_data.items():
        setattr(db_note, key, value)
    db_note.version += 1
    db.commit()
    db.refresh(db_note)
    return db_note


# --- MODIFIED: THE MAIN FIX IS HERE ---
async def delete_note(db: Session, note_id: int) -> Optional[models.Note]:
    """Delete a note and all of its descendants from the database."""
    db_note = await get_note_by_id(db, note_id)
    if not db_note:
        return None

    if db_note.owner_id != 1:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Only notes owned by user_id=1 can be deleted."
        )

    # 1. Find all children, grandchildren, etc.
    descendant_ids = _get_all_descendant_ids(db, note_id)
    ids_to_delete = [note_id] + descendant_ids

    logger.info(f"Deleting note ID: {note_id} and its {len(descendant_ids)} descendants. Total: {len(ids_to_delete)}.")

    # 2. Perform a bulk delete in a single transaction
    db.query(models.Note).filter(models.Note.id.in_(ids_to_delete)).delete(synchronize_session=False)
    db.commit()

    # 3. Return the original (now deleted) note as confirmation
    return db_note

# --- The rest of the functions (read operations) remain unchanged ---
async def get_all_notes_stream(db: Session, batch_size: int = 100) -> Generator[List[models.Note], None, None]:
    logger.info(f"Streaming all notes with batch_size {batch_size}.")
    offset = 0
    while True:
        db_notes_batch = db.query(models.Note).offset(offset).limit(batch_size).all()
        if not db_notes_batch:
            break
        yield db_notes_batch
        if len(db_notes_batch) < batch_size:
            break
        offset += batch_size
    logger.info("Finished streaming all notes.")

async def get_notes_by_user_stream(db: Session, owner_id: int, batch_size: int = 100) -> Generator[List[models.Note], None, None]:
    logger.info(f"Streaming notes for owner_id {owner_id} with batch_size {batch_size}.")
    offset = 0
    while True:
        db_notes_batch = db.query(models.Note).filter(models.Note.owner_id == owner_id).offset(offset).limit(batch_size).all()
        if not db_notes_batch:
            break
        yield db_notes_batch
        if len(db_notes_batch) < batch_size:
            break
        offset += batch_size
    logger.info(f"Finished streaming notes for owner_id {owner_id}.")

async def get_all_notes_count(db: Session) -> int:
    count = db.query(func.count(models.Note.id)).scalar()
    return count or 0

async def get_notes_by_user_count(db: Session, owner_id: int) -> int:
    count = db.query(func.count(models.Note.id)).filter(models.Note.owner_id == owner_id).scalar()
    return count or 0