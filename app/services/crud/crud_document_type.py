# app/services/crud/crud_document_type.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from typing import Optional, List

from app import models # Your SQLAlchemy models
from app import schemas # Your Pydantic schemas

def get_document_type(db: Session, document_type_id: int) -> Optional[models.DocumentType]:
    """
    Retrieve a document type by its ID.
    """
    return db.query(models.DocumentType).filter(models.DocumentType.id == document_type_id).first()

def get_document_type_by_name(db: Session, name: str) -> Optional[models.DocumentType]:
    """
    Retrieve a document type by its name.
    """
    return db.query(models.DocumentType).filter(models.DocumentType.name == name).first()

def get_all_document_types(db: Session, skip: int = 0, limit: int = 100) -> List[models.DocumentType]:
    """
    Retrieve all document types with pagination.
    """
    return db.query(models.DocumentType).offset(skip).limit(limit).all()

def create_document_type(db: Session, doc_type_in: schemas.DocumentTypeCreate) -> models.DocumentType:
    """
    Create a new document type.
    """
    # Assuming version is handled here (e.g., starts at 0) or defaulted in model
    # If 'version' is not in DocumentTypeCreate, you need to add it here.
    # For simplicity, let's assume 'version' is not part of the input schema and defaults to 0
    db_doc_type = models.DocumentType(
        name=doc_type_in.name,
        version=0  # Or any other initial version logic
    )
    db.add(db_doc_type)
    try:
        db.commit()
        db.refresh(db_doc_type)
    except IntegrityError:
        db.rollback()
        # This could happen if 'name' is unique and already exists
        # Or if another constraint is violated.
        # You might want to raise a custom exception or re-raise
        raise # Or handle more gracefully, e.g., by fetching the existing one
    return db_doc_type

def get_or_create_document_type(db: Session, name: str) -> models.DocumentType:
    """
    Retrieves a document type by name, or creates it if it doesn't exist.
    This is useful for ensuring a type like "Web Crawl" exists.
    """
    db_doc_type = get_document_type_by_name(db, name=name)
    if not db_doc_type:
        print(f"DocumentType '{name}' not found, creating...")
        doc_type_schema = schemas.DocumentTypeCreate(name=name)
        db_doc_type = create_document_type(db, doc_type_in=doc_type_schema)
        print(f"Created DocumentType '{name}' with ID: {db_doc_type.id}")
    return db_doc_type

def update_document_type(
    db: Session,
    document_type_id: int,
    doc_type_update: schemas.DocumentTypeUpdate # Assuming you create a DocumentTypeUpdate schema
) -> Optional[models.DocumentType]:
    """
    Update an existing document type.
    (Requires a DocumentTypeUpdate Pydantic schema)
    """
    db_doc_type = get_document_type(db, document_type_id)
    if not db_doc_type:
        return None

    update_data = doc_type_update.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_doc_type, key, value)

    # Increment version or handle as per your versioning strategy
    db_doc_type.version = (db_doc_type.version or 0) + 1

    db.add(db_doc_type)
    db.commit()
    db.refresh(db_doc_type)
    return db_doc_type

def delete_document_type(db: Session, document_type_id: int) -> Optional[models.DocumentType]:
    """
    Delete a document type.
    (Consider implications: what if documents reference this type?)
    """
    db_doc_type = get_document_type(db, document_type_id)
    if not db_doc_type:
        return None
    db.delete(db_doc_type)
    db.commit()
    return db_doc_type