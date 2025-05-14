# app/api/v1/endpoints/document_types.py
import logging
from typing import List, Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas, models
from app.services.crud import crud_document_type
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

DbDependency = Annotated[Session, Depends(get_db)]

@router.get(
    "/",
    response_model=List[schemas.document.DocumentTypeResponse],
    summary="List all Document Types",
    description="Retrieves a list of all available document types, with optional pagination.",
    tags=["V1 - KB - Document Types"] # New Tag
)
async def list_document_types(
    db: DbDependency,
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination."),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return.")
) -> List[models.DocumentType]:
    """
    Get a list of all document types.
    Supports pagination (`skip`, `limit`).
    """
    document_types = crud_document_type.get_all_document_types(db, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(document_types)} document types with skip={skip}, limit={limit}.")
    return document_types

# Placeholder for future CRUD operations on DocumentTypes if needed:
# @router.post("/", response_model=schemas.document.DocumentTypeResponse, status_code=status.HTTP_201_CREATED)
# async def create_document_type_endpoint(doc_type_in: schemas.document.DocumentTypeCreate, db: DbDependency):
#     # ... implementation using crud_document_type.create_document_type ...
#     pass

# @router.get("/{document_type_id}", response_model=schemas.document.DocumentTypeResponse)
# async def get_document_type_endpoint(document_type_id: int, db: DbDependency):
#     # ... implementation using crud_document_type.get_document_type ...
#     pass

# @router.put("/{document_type_id}", response_model=schemas.document.DocumentTypeResponse)
# async def update_document_type_endpoint(document_type_id: int, doc_type_update: schemas.document.DocumentTypeUpdate, db: DbDependency):
#     # ... implementation using crud_document_type.update_document_type ...
#     pass

# @router.delete("/{document_type_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_document_type_endpoint(document_type_id: int, db: DbDependency):
#     # ... implementation using crud_document_type.delete_document_type ...
#     pass