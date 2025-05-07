# app/services/crud/crud_note_document.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List

from app import models # Your SQLAlchemy models
from app import schemas # Your Pydantic schemas (NoteDocumentCreate, NoteDocumentResponse)

def get_note_document_link(
    db: Session, note_id: int, document_id: int
) -> Optional[models.NoteDocument]:
    """
    Retrieve a specific link between a note and a document.
    Uses the column names from your NoteDocument model.
    """
    return db.query(models.NoteDocument).filter(
        models.NoteDocument.note_documents_id == note_id,
        models.NoteDocument.document_id == document_id
    ).first()

def create_note_document_link(
    db: Session, note_id: int, document_id: int
) -> models.NoteDocument:
    """
    Create a link between a note and a document in the NoteDocument table.
    """
    # Check if the link already exists to prevent duplicates if desired,
    # though the composite PK should handle this at DB level.
    existing_link = get_note_document_link(db, note_id, document_id)
    if existing_link:
        # Depending on requirements, you might return the existing link
        # or raise an error indicating it already exists.
        # For now, let's assume returning existing is fine.
        print(f"Link between Note ID {note_id} and Document ID {document_id} already exists.")
        return existing_link

    # Ensure note and document actually exist before creating a link
    note = db.query(models.Note).filter(models.Note.id == note_id).first()
    if not note:
        raise ValueError(f"Note with ID {note_id} not found. Cannot create link.")
    document = db.query(models.Document).filter(models.Document.id == document_id).first()
    if not document:
        raise ValueError(f"Document with ID {document_id} not found. Cannot create link.")


    # Use the column names as defined in your models.NoteDocument
    # For your model: `note_documents_id` and `document_id`
    db_link = models.NoteDocument(
        note_documents_id=note_id,
        document_id=document_id
    )
    db.add(db_link)
    try:
        db.commit()
        db.refresh(db_link)
    except IntegrityError as e:
        db.rollback()
        # This could happen due to FK constraint violation (if note/doc deleted concurrently)
        # Or if PK constraint violated (if somehow existing_link check failed or race condition)
        print(f"IntegrityError creating link: {e}")
        raise  # Re-raise or handle more gracefully
    return db_link

def get_documents_for_note(db: Session, note_id: int) -> List[models.Document]:
    """
    Retrieve all documents linked to a specific note.
    """
    # This query joins NoteDocument with Document table
    return db.query(models.Document).join(
        models.NoteDocument, models.NoteDocument.document_id == models.Document.id
    ).filter(models.NoteDocument.note_documents_id == note_id).all()

def get_notes_for_document(db: Session, document_id: int) -> List[models.Note]:
    """
    Retrieve all notes linked to a specific document.
    """
    # This query joins NoteDocument with Note table
    return db.query(models.Note).join(
        models.NoteDocument, models.NoteDocument.note_documents_id == models.Note.id
    ).filter(models.NoteDocument.document_id == document_id).all()

def delete_note_document_link(
    db: Session, note_id: int, document_id: int
) -> Optional[models.NoteDocument]:
    """
    Delete a specific link between a note and a document.
    """
    db_link = get_note_document_link(db, note_id, document_id)
    if not db_link:
        return None # Link doesn't exist
    db.delete(db_link)
    db.commit()
    return db_link

def delete_all_links_for_note(db: Session, note_id: int) -> int:
    """
    Delete all document links for a specific note.
    Returns the number of links deleted.
    """
    num_deleted = db.query(models.NoteDocument).filter(
        models.NoteDocument.note_documents_id == note_id
    ).delete(synchronize_session=False) # Use False for bulk delete efficiency
    db.commit()
    return num_deleted

def delete_all_links_for_document(db: Session, document_id: int) -> int:
    """
    Delete all note links for a specific document.
    Returns the number of links deleted.
    """
    num_deleted = db.query(models.NoteDocument).filter(
        models.NoteDocument.document_id == document_id
    ).delete(synchronize_session=False)
    db.commit()
    return num_deleted