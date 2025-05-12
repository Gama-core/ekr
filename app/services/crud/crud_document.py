# app/services/crud/crud_document.py

from sqlalchemy.orm import Session
from typing import Optional, List

from app import models # Your SQLAlchemy models
from app import schemas # Your Pydantic schemas
from app.core.config import settings # For SYSTEM_USER_ID

def get_document(db: Session, document_id: int) -> Optional[models.Document]:
    """
    Retrieve a document by its ID.
    """
    return db.query(models.Document).filter(models.Document.id == document_id).first()

def get_documents_by_owner(
    db: Session, owner_id: int, skip: int = 0, limit: int = 100
) -> List[models.Document]:
    """
    Retrieve documents owned by a specific user with pagination.
    """
    return db.query(models.Document).filter(models.Document.owned_by_id == owner_id).offset(skip).limit(limit).all()

def get_all_documents(db: Session, skip: int = 0, limit: int = 100) -> List[models.Document]:
    """
    Retrieve all documents with pagination.
    """
    return db.query(models.Document).offset(skip).limit(limit).all()

def create_document(
    db: Session,
    doc_in: schemas.DocumentCreate,
    owner_id: Optional[int] = None  # Allow explicit owner or use system user
) -> models.Document:
    """
    Create a new document.
    The `doc_in` schema should provide doc_type_id, path, name, etc.
    The `owner_id` can be passed explicitly or defaults to SYSTEM_USER_ID.
    """
    final_owner_id = owner_id if owner_id is not None else settings.SYSTEM_USER_ID

    # Ensure the owner exists if final_owner_id is not None.
    # This check can be more elaborate if needed.
    if final_owner_id:
        owner = db.query(models.AppUser).filter(models.AppUser.id == final_owner_id).first()
        if not owner:
            # Handle case where owner_id is provided but user doesn't exist
            # Or if SYSTEM_USER_ID is configured but doesn't exist in DB
            raise ValueError(f"Owner user with ID {final_owner_id} not found.")

    db_doc = models.Document(
        doc_type_id=doc_in.doc_type_id,
        comment=doc_in.comment,
        mime_type=doc_in.mime_type,
        owned_by_id=final_owner_id, # Use the determined owner ID
        url=doc_in.url,
        path=doc_in.path,
        name=doc_in.name,
        #version=0  # Or your initial version logic
    )
    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def update_document(
    db: Session,
    document_id: int,
    doc_update: schemas.DocumentUpdate # Assuming you create a DocumentUpdate schema
) -> Optional[models.Document]:
    """
    Update an existing document.
    (Requires a DocumentUpdate Pydantic schema)
    """
    db_doc = get_document(db, document_id)
    if not db_doc:
        return None

    update_data = doc_update.model_dump(exclude_unset=True) # Pydantic v2
    # For Pydantic v1: update_data = doc_update.dict(exclude_unset=True)

    for key, value in update_data.items():
        setattr(db_doc, key, value)

    # Increment version or handle as per your versioning strategy
    db_doc.version = (db_doc.version or 0) + 1

    db.add(db_doc)
    db.commit()
    db.refresh(db_doc)
    return db_doc

def delete_document(db: Session, document_id: int) -> Optional[models.Document]:
    """
    Delete a document.
    (Consider implications: linked notes in NoteDocument, file system cleanup if applicable)
    """
    db_doc = get_document(db, document_id)
    if not db_doc:
        return None

    # Before deleting, you might need to handle related NoteDocument entries.
    # Option 1: Cascade delete configured in DB or SQLAlchemy relationship.
    # Option 2: Manually delete related NoteDocument entries here.
    # e.g., db.query(models.NoteDocument).filter(models.NoteDocument.document_id == document_id).delete()

    db.delete(db_doc)
    db.commit()
    return db_doc