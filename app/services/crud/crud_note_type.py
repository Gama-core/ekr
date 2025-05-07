# app/services/crud/crud_note_type.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List

from app import models # Your SQLAlchemy models
from app import schemas # Your Pydantic schemas

def get_note_type(db: Session, note_type_id: int) -> Optional[models.NoteType]:
    """
    Retrieve a note type by its ID.
    """
    return db.query(models.NoteType).filter(models.NoteType.id == note_type_id).first()

def get_note_type_by_name(db: Session, name: str) -> Optional[models.NoteType]:
    """
    Retrieve a note type by its name.
    """
    return db.query(models.NoteType).filter(models.NoteType.name == name).first()

def get_all_note_types(db: Session, skip: int = 0, limit: int = 100) -> List[models.NoteType]:
    """
    Retrieve all note types with pagination.
    """
    return db.query(models.NoteType).offset(skip).limit(limit).all()

def create_note_type(db: Session, note_type_in: schemas.NoteTypeCreate) -> models.NoteType:
    """
    Create a new note type.
    """
    # Your NoteType model's 'name' column in the DDL did not have a unique constraint.
    # If it should be unique, add it to the model and handle potential IntegrityError here.
    # existing_type = get_note_type_by_name(db, name=note_type_in.name)
    # if existing_type:
    #     raise ValueError(f"NoteType with name '{note_type_in.name}' already exists.")

    db_note_type = models.NoteType(
        name=note_type_in.name,
        version=0  # Or your initial version logic
    )
    db.add(db_note_type)
    try:
        db.commit()
        db.refresh(db_note_type)
    except IntegrityError:
        db.rollback()
        # This might happen if 'name' becomes unique and already exists,
        # or if another constraint is violated.
        raise
    return db_note_type

def get_or_create_note_type(db: Session, name: str) -> models.NoteType:
    """
    Retrieves a note type by name, or creates it if it doesn't exist.
    """
    db_note_type = get_note_type_by_name(db, name=name)
    if not db_note_type:
        print(f"NoteType '{name}' not found, creating...")
        note_type_schema = schemas.NoteTypeCreate(name=name)
        db_note_type = create_note_type(db, note_type_in=note_type_schema)
        print(f"Created NoteType '{name}' with ID: {db_note_type.id}")
    return db_note_type

def update_note_type(
    db: Session,
    note_type_id: int,
    note_type_update: schemas.NoteTypeUpdate # Assuming you create a NoteTypeUpdate schema
) -> Optional[models.NoteType]:
    """
    Update an existing note type.
    (Requires a NoteTypeUpdate Pydantic schema)
    """
    db_note_type = get_note_type(db, note_type_id)
    if not db_note_type:
        return None

    update_data = note_type_update.model_dump(exclude_unset=True)

    # If 'name' is updatable and should be unique, check for conflicts:
    # if "name" in update_data and update_data["name"] != db_note_type.name:
    #     existing_type = get_note_type_by_name(db, name=update_data["name"])
    #     if existing_type and existing_type.id != note_type_id:
    #         raise ValueError(f"NoteType name '{update_data['name']}' already taken.")

    for key, value in update_data.items():
        setattr(db_note_type, key, value)

    db_note_type.version = (db_note_type.version or 0) + 1
    db.add(db_note_type)
    db.commit()
    db.refresh(db_note_type)
    return db_note_type

def delete_note_type(db: Session, note_type_id: int) -> Optional[models.NoteType]:
    """
    Delete a note type.
    (Consider implications: what if notes reference this type?)
    """
    db_note_type = get_note_type(db, note_type_id)
    if not db_note_type:
        return None
    # Handle notes that reference this type_id.
    # Option 1: DB CASCADE on FK or SET NULL.
    # Option 2: Manually update referencing notes (e.g., set note.type_id to NULL or a default type_id).
    # Option 3: Prevent deletion if it's in use.
    # db.query(models.Note).filter(models.Note.type_id == note_type_id).update({"type_id": None})
    db.delete(db_note_type)
    db.commit()
    return db_note_type