# app/api/v1/endpoints/documents.py
import logging
import os
import shutil
from pathlib import Path
from typing import List, Optional, Annotated

from fastapi import (
    APIRouter, Depends, HTTPException, status, Query,
    UploadFile, File, Form
)
from sqlalchemy.orm import Session

from app import schemas, models # Assuming schemas.crud and models.crud are available
from app.services.crud import crud_document, crud_note_document, crud_document_type # Make sure crud_note is imported if used
from app.services.crud import crud_note # Import crud_note if used by link_to_note_id logic
from app.core.database import get_db
from app.core.config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

DbDependency = Annotated[Session, Depends(get_db)]

# Define a directory for uploaded files (ensure this directory exists or is created)
# For production, use a more robust storage solution (S3, etc.)
UPLOAD_DIR = Path("./uploaded_files")
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)


# Helper for owner_id - replace with actual authenticated user logic later
def get_current_user_id_or_default(db_user_id: Optional[int] = None) -> int:
    if db_user_id:
        return db_user_id
    return settings.SYSTEM_USER_ID

@router.post(
    "/upload",
    response_model=schemas.document.DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a File and Create Document Record",
    description="Uploads a physical file, stores it, and creates a corresponding Document record in the database. Optionally links it to a note.",
)
async def upload_document(
    db: DbDependency,
    file: UploadFile = File(..., description="The file to upload."),
    doc_type_id: int = Form(..., description="ID of the document type."),
    comment: Optional[str] = Form(None, description="Optional comment for the document."),
    name: Optional[str] = Form(None, description="Optional name for the document (defaults to filename)."),
    link_to_note_id: Optional[int] = Form(None, description="Optional ID of a Note to link this document to."),
    # current_user_id: int = Depends(get_current_user_id_or_default) # For future auth
):
    """
    Upload a document file.
    - **file**: The actual file being uploaded.
    - **doc_type_id**: The ID of the document's type (e.g., PDF, Image).
    - **comment**: An optional comment about the document.
    - **name**: An optional name for the document. If not provided, the original filename is used.
    - **link_to_note_id**: Optional. If provided, links the new document to the specified note.
    """
    owner_id_to_use = get_current_user_id_or_default()

    doc_type = crud_document_type.get_document_type(db, doc_type_id)
    if not doc_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"DocumentType with ID {doc_type_id} not found.")

    filename = Path(file.filename).name if file.filename else "uploaded_file"
    filename = "".join(c if c.isalnum() or c in ('.', '_', '-') else '_' for c in filename)
    if not name:
        name_to_use = filename
    else:
        name_to_use = name

    # Construct the initial file path within UPLOAD_DIR
    # unique_file_path will be the actual path where the file is saved on disk
    file_path_in_upload_dir = UPLOAD_DIR / filename
    unique_file_path = file_path_in_upload_dir # Start with the base name
    counter = 1
    while unique_file_path.exists(): # Check existence of the full path
        name_part, ext_part = os.path.splitext(filename) # Use original sanitized filename for parts
        unique_file_path = UPLOAD_DIR / f"{name_part}_{counter}{ext_part}"
        counter += 1

    try:
        with open(unique_file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        logger.info(f"File '{filename}' uploaded to '{unique_file_path}'")
    except Exception as e:
        logger.exception(f"Could not save uploaded file '{filename}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not save uploaded file.")
    finally:
        file.file.close()

    # --- FIX 1 APPLIED HERE for path storage ---
    # Store only the final, unique filename (including any counter) in the database path field.
    # unique_file_path.name will give "innumeracy.pdf" or "innumeracy_1.pdf" etc.
    path_to_store_in_db = unique_file_path.name
    # --- End FIX 1 ---

    doc_in = schemas.DocumentCreate(
        doc_type_id=doc_type_id,
        comment=comment,
        mime_type=file.content_type,
        owned_by_id=owner_id_to_use,
        url=None,
        path=path_to_store_in_db, # Use the corrected path for DB storage
        name=name_to_use
    )

    try:
        created_document = crud_document.create_document(db=db, doc_in=doc_in, owner_id=owner_id_to_use)
        logger.info(f"Document record created with ID: {created_document.id} for file: '{name_to_use}' (DB path: '{path_to_store_in_db}')")

        if link_to_note_id:
            note = crud_note.get_note(db, note_id=link_to_note_id)
            if not note:
                logger.warning(f"Note with ID {link_to_note_id} not found. Document {created_document.id} created but not linked.")
            else:
                crud_note_document.create_note_document_link(db, note_id=link_to_note_id, document_id=created_document.id)
                logger.info(f"Linked Document ID {created_document.id} to Note ID {link_to_note_id}.")

        return created_document
    except ValueError as ve:
        logger.error(f"ValueError during document creation/linking: {ve}")
        if unique_file_path.exists(): # Clean up file if DB fails
            os.remove(unique_file_path)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Could not create document record for '{name_to_use}': {e}")
        if unique_file_path.exists(): # Clean up file if DB fails
            os.remove(unique_file_path)
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create document record.")


@router.post(
    "/from-url",
    response_model=schemas.document.DocumentResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Document Record from URL",
    description="Creates a Document record for an external URL. Optionally links it to a note.",
)
async def create_document_from_url(
    request: schemas.document.DocumentCreateFromUrlRequest,
    db: DbDependency,
):
    owner_id_to_use = get_current_user_id_or_default()

    doc_type = crud_document_type.get_document_type(db, request.doc_type_id)
    if not doc_type:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"DocumentType with ID {request.doc_type_id} not found.")

    doc_in = schemas.DocumentCreate(
        doc_type_id=request.doc_type_id,
        comment=request.comment,
        mime_type="text/url",
        owned_by_id=owner_id_to_use,
        url=str(request.url),
        path=str(request.url), # For URL type, path is the URL
        name=request.name
    )

    try:
        created_document = crud_document.create_document(db=db, doc_in=doc_in, owner_id=owner_id_to_use)
        logger.info(f"Document record created with ID: {created_document.id} for URL: '{request.url}'")

        if request.link_to_note_id:
            note = crud_note.get_note(db, note_id=request.link_to_note_id)
            if not note:
                logger.warning(f"Note with ID {request.link_to_note_id} not found. Document {created_document.id} created but not linked.")
            else:
                crud_note_document.create_note_document_link(db, note_id=request.link_to_note_id, document_id=created_document.id)
                logger.info(f"Linked Document ID {created_document.id} to Note ID {request.link_to_note_id}.")
        return created_document
    except ValueError as ve:
        logger.error(f"ValueError during document creation from URL: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Could not create document record from URL '{request.url}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create document record from URL.")


@router.get(
    "/",
    response_model=List[schemas.document.DocumentResponse],
    summary="List Documents",
    description="Retrieves a list of document records, with optional pagination and filtering.",
)
async def list_documents(
    db: DbDependency,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    owner_id: Optional[int] = Query(None),
    doc_type_id: Optional[int] = Query(None),
    name_contains: Optional[str] = Query(None, min_length=1, max_length=100),
) -> List[models.Document]:
    query = db.query(models.Document)
    if owner_id is not None:
        query = query.filter(models.Document.owned_by_id == owner_id)
    if doc_type_id is not None:
        query = query.filter(models.Document.doc_type_id == doc_type_id)
    if name_contains:
        query = query.filter(models.Document.name.ilike(f"%{name_contains}%"))

    documents = query.order_by(models.Document.id.desc()).offset(skip).limit(limit).all()
    logger.info(f"Retrieved {len(documents)} documents with skip={skip}, limit={limit}.")
    return documents


@router.get(
    "/{document_id}",
    response_model=schemas.document.DocumentResponse,
    summary="Get a specific Document",
    description="Retrieves metadata of a single document by its ID.",
)
async def get_document(
    document_id: int,
    db: DbDependency,
) -> models.Document:
    db_document = crud_document.get_document(db, document_id=document_id)
    if db_document is None:
        logger.warning(f"Document with ID {document_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")
    logger.info(f"Retrieved document ID: {db_document.id}, Name: '{db_document.name}'")
    return db_document


@router.put(
    "/{document_id}",
    response_model=schemas.document.DocumentResponse,
    summary="Update Document Metadata",
    description="Modifies metadata of an existing document record. This does not re-upload the file.",
)
async def update_document(
    document_id: int,
    doc_update: schemas.document.DocumentUpdate,
    db: DbDependency,
) -> models.Document:
    db_doc = crud_document.get_document(db, document_id=document_id)
    if db_doc is None:
        logger.warning(f"Attempted to update non-existent document with ID: {document_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    try:
        updated_doc = crud_document.update_document(db=db, document_id=document_id, doc_update=doc_update)
        if updated_doc is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found after update attempt")
        logger.info(f"Document ID: {updated_doc.id} metadata updated successfully.")
        return updated_doc
    except ValueError as ve:
        logger.error(f"ValueError during document update for ID {document_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Could not update document ID {document_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update document metadata.")


@router.delete(
    "/{document_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Document",
    description="Removes a document record and its associated stored file (if any).",
)
async def delete_document(
    document_id: int,
    db: DbDependency,
):
    db_doc_to_delete = crud_document.get_document(db, document_id=document_id)
    if db_doc_to_delete is None:
        logger.warning(f"Attempted to delete non-existent document with ID: {document_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found")

    # This will retrieve the filename (e.g., "innumeracy_1.pdf") from the database
    stored_filename_in_db_path = db_doc_to_delete.path
    is_uploaded_file = not (db_doc_to_delete.url and db_doc_to_delete.path == db_doc_to_delete.url)

    try:
        deleted_doc_record = crud_document.delete_document(db, document_id=document_id)
        if deleted_doc_record is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Document not found during delete")
        logger.info(f"Document record ID: {document_id} deleted from database.")

        if is_uploaded_file and stored_filename_in_db_path:
            # --- FIX 1 APPLIED HERE for path reconstruction during delete ---
            # Reconstruct the full path to the file using UPLOAD_DIR and the stored filename
            file_to_remove = UPLOAD_DIR / stored_filename_in_db_path
            # --- End FIX 1 ---

            if file_to_remove.exists() and file_to_remove.is_file():
                try:
                    os.remove(file_to_remove)
                    logger.info(f"Associated file '{file_to_remove}' deleted from storage.")
                except OSError as ose:
                    logger.error(f"OSError deleting file '{file_to_remove}': {ose}. DB record was still deleted.")
            else:
                logger.warning(f"Associated file '{file_to_remove}' not found or not a file for deletion. DB record was deleted.")
    except Exception as e:
        logger.exception(f"Could not delete document ID {document_id} or its file: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not complete document deletion process.")