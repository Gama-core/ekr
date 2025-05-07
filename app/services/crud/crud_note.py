# app/services/crud/crud_note.py

from sqlalchemy.orm import Session
from typing import Optional, List
from datetime import datetime

from app import models # Your SQLAlchemy models
from app import schemas # Your Pydantic schemas
from app.core.config import settings # For default owner if needed, though typically owner_id is explicit

def get_note(db: Session, note_id: int) -> Optional[models.Note]:
    """
    Retrieve a note by its ID.
    """
    return db.query(models.Note).filter(models.Note.id == note_id).first()

def get_notes_by_owner(
    db: Session, owner_id: int, skip: int = 0, limit: int = 100
) -> List[models.Note]:
    """
    Retrieve notes owned by a specific user with pagination.
    """
    return db.query(models.Note).filter(models.Note.owner_id == owner_id).offset(skip).limit(limit).all()

def get_all_notes(db: Session, skip: int = 0, limit: int = 100) -> List[models.Note]:
    """
    Retrieve all notes with pagination.
    """
    return db.query(models.Note).offset(skip).limit(limit).all()

def create_note(
    db: Session,
    note_in: schemas.NoteCreate,
    owner_id: int # Explicitly require owner_id for note creation
) -> models.Note:
    """
    Create a new note.
    The `owner_id` must be provided.
    """
    # Ensure the owner exists. This check can be more elaborate.
    owner = db.query(models.AppUser).filter(models.AppUser.id == owner_id).first()
    if not owner:
        raise ValueError(f"Owner user with ID {owner_id} not found. Cannot create note.")

    # Prepare data for the model, ensuring owner_id is set from the argument
    # and not from note_in (which might have it as optional)
    model_data = note_in.model_dump(exclude_unset=True)
    model_data['owner_id'] = owner_id # Override with the provided owner_id

    db_note = models.Note(
        **model_data,
        version=0,  # Or your initial version logic
        creation_date=datetime.utcnow() # Set creation date explicitly
    )

    # If note_in.owner_id was part of the schema and potentially None, this ensures it's set.
    # However, it's better to make owner_id mandatory in the service layer call.
    # if 'owner_id' not in model_data or model_data['owner_id'] is None:
    #     db_note.owner_id = owner_id

    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def update_note(
    db: Session,
    note_id: int,
    note_update: schemas.NoteUpdate # Assuming you create a NoteUpdate schema
) -> Optional[models.Note]:
    """
    Update an existing note.
    (Requires a NoteUpdate Pydantic schema)
    """
    db_note = get_note(db, note_id)
    if not db_note:
        return None

    update_data = note_update.model_dump(exclude_unset=True) # Pydantic v2
    # For Pydantic v1: update_data = note_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        # Special handling for owner_id if it's updatable, ensure new owner exists
        if key == "owner_id" and value is not None:
            new_owner = db.query(models.AppUser).filter(models.AppUser.id == value).first()
            if not new_owner:
                raise ValueError(f"New owner user with ID {value} not found. Cannot update note owner.")
        setattr(db_note, key, value)

    # Increment version or handle as per your versioning strategy
    db_note.version = (db_note.version or 0) + 1

    db.add(db_note)
    db.commit()
    db.refresh(db_note)
    return db_note

def delete_note(db: Session, note_id: int) -> Optional[models.Note]:
    """
    Delete a note.
    (Consider implications: linked documents in NoteDocument, child notes, links)
    """
    db_note = get_note(db, note_id)
    if not db_note:
        return None

    # Before deleting, you might need to handle:
    # 1. Related NoteDocument entries:
    #    db.query(models.NoteDocument).filter(models.NoteDocument.note_documents_id == note_id).delete(synchronize_session=False)
    # 2. Child notes (if parent_id relationship has cascade delete not set up):
    #    Recursively delete children or set their parent_id to NULL.
    # 3. Links where this note is a source or destination:
    #    db.query(models.Link).filter((models.Link.source_id == note_id) | (models.Link.destination_id == note_id)).delete(synchronize_session=False)
    # The 'synchronize_session=False' is often needed for bulk deletes before a commit.

    db.delete(db_note)
    db.commit()
    return db_note