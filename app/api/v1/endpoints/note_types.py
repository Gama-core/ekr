# app/api/v1/endpoints/note_types.py
import logging
from typing import List, Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app import schemas, models
from app.services.crud import crud_note_type
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

DbDependency = Annotated[Session, Depends(get_db)]

@router.get(
    "/",
    response_model=List[schemas.note.NoteTypeResponse],
    summary="List all Note Types",
    description="Retrieves a list of all available note types, with optional pagination.",
    tags=["V1 - KB - Note Types"] # New Tag
)
async def list_note_types(
    db: DbDependency,
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination."),
    limit: int = Query(100, ge=1, le=200, description="Maximum number of records to return.")
) -> List[models.NoteType]:
    """
    Get a list of all note types.
    Supports pagination (`skip`, `limit`).
    """
    note_types = crud_note_type.get_all_note_types(db, skip=skip, limit=limit)
    logger.info(f"Retrieved {len(note_types)} note types with skip={skip}, limit={limit}.")
    return note_types

# Placeholder for future CRUD operations on NoteTypes if needed:
# @router.post("/", response_model=schemas.note.NoteTypeResponse, status_code=status.HTTP_201_CREATED)
# async def create_note_type_endpoint(note_type_in: schemas.note.NoteTypeCreate, db: DbDependency):
#     # ... implementation using crud_note_type.create_note_type ...
#     pass

# @router.get("/{note_type_id}", response_model=schemas.note.NoteTypeResponse)
# async def get_note_type_endpoint(note_type_id: int, db: DbDependency):
#     # ... implementation using crud_note_type.get_note_type ...
#     pass

# @router.put("/{note_type_id}", response_model=schemas.note.NoteTypeResponse)
# async def update_note_type_endpoint(note_type_id: int, note_type_update: schemas.note.NoteTypeUpdate, db: DbDependency):
#     # ... implementation using crud_note_type.update_note_type ...
#     pass

# @router.delete("/{note_type_id}", status_code=status.HTTP_204_NO_CONTENT)
# async def delete_note_type_endpoint(note_type_id: int, db: DbDependency):
#     # ... implementation using crud_note_type.delete_note_type ...
#     pass