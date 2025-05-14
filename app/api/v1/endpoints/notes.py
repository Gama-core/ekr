# app/api/v1/endpoints/notes.py
import logging
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import schemas, models
from app.services.crud import crud_note
from app.core.database import get_db
from app.core.config import settings # For default owner_id if no auth

logger = logging.getLogger(__name__)
router = APIRouter()

DbDependency = Annotated[Session, Depends(get_db)]

# Helper for owner_id - replace with actual authenticated user logic later
def get_current_user_id_or_default(db_user_id: Optional[int] = None) -> int:
    # In a real app, this would come from a Depends(get_current_active_user)
    if db_user_id:
        return db_user_id
    return settings.SYSTEM_USER_ID # Fallback to system user for now

@router.post(
    "/",
    response_model=schemas.note.NoteResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Note",
    description="Creates a new note in the knowledge base. `owner_id` will default to system user if not provided or if authentication is not implemented.",
)
async def create_note(
    note_in: schemas.note.NoteCreate,
    db: DbDependency,
    # current_user_id: int = Depends(get_current_user_id_or_default) # Example for future auth
) -> models.Note:
    """
    Create a new note.
    - **title**: The title of the note.
    - **text**: The main content of the note.
    - **type_id**: Optional ID of the note type.
    - **parent_id**: Optional ID of the parent note for hierarchical structure.
    - **link_id**: Optional ID of a primary link associated with this note.
    - **color**: Optional color for the note (e.g., for UI).
    """
    # If note_in.owner_id is None (as it's Optional in NoteCreate),
    # crud_note.create_note expects an explicit owner_id argument.
    # For now, we'll use a default or allow it from schema if auth is not yet in place.
    owner_id_to_use = note_in.owner_id if note_in.owner_id is not None else get_current_user_id_or_default()

    try:
        created_note = crud_note.create_note(db=db, note_in=note_in, owner_id=owner_id_to_use)
        logger.info(f"Note created with ID: {created_note.id} and title: '{created_note.title}'")
        return created_note
    except ValueError as ve: # Catch specific errors like owner not found
        logger.error(f"ValueError during note creation: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Could not create note: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create note.")

@router.get(
    "/",
    response_model=List[schemas.note.NoteResponse],
    summary="List Notes",
    description="Retrieves a list of notes, with optional pagination and filtering.",
)
async def list_notes(
    db: DbDependency,
    skip: int = Query(0, ge=0, description="Number of records to skip for pagination."),
    limit: int = Query(100, ge=1, le=500, description="Maximum number of records to return."),
    owner_id: Optional[int] = Query(None, description="Filter notes by owner ID."),
    parent_id: Optional[int] = Query(None, description="Filter notes by parent ID. Use 0 or null for top-level notes (implementation specific)."),
    type_id: Optional[int] = Query(None, description="Filter notes by note type ID."),
    title_contains: Optional[str] = Query(None, min_length=1, max_length=100, description="Filter notes by title containing this string (case-insensitive)."),
    # TODO: Add more filters like date range, color, etc.
) -> List[models.Note]:
    """
    Get a list of notes.
    Supports pagination (`skip`, `limit`) and filtering by:
    - `owner_id`
    - `parent_id` (Note: Filtering for 'no parent' might require special handling in CRUD)
    - `type_id`
    - `title_contains`
    """
    # Basic implementation, advanced filtering would require a dedicated CRUD function
    query = db.query(models.Note)
    if owner_id is not None:
        query = query.filter(models.Note.owner_id == owner_id)
    if parent_id is not None: # Note: To get top-level notes (parent_id IS NULL), this needs adjustment in CRUD.
        query = query.filter(models.Note.parent_id == parent_id)
    if type_id is not None:
        query = query.filter(models.Note.type_id == type_id)
    if title_contains:
        query = query.filter(models.Note.title.ilike(f"%{title_contains}%")) # Case-insensitive search

    notes = query.order_by(models.Note.id.desc()).offset(skip).limit(limit).all()
    logger.info(f"Retrieved {len(notes)} notes with skip={skip}, limit={limit}.")
    return notes

@router.get(
    "/{note_id}",
    response_model=schemas.note.NoteResponse, # Consider a more detailed response schema if including children/docs
    summary="Get a specific Note",
    description="Retrieves details of a single note by its ID. Optionally include related data.",
)
async def get_note(
    note_id: int,
    db: DbDependency,
    # include_children: bool = Query(False, description="Set to true to include direct children of the note."),
    # include_documents: bool = Query(False, description="Set to true to include linked documents."),
    # include_links: bool = Query(False, description="Set to true to include associated links.")
) -> models.Note:
    """
    Get a specific note by ID.
    Future enhancements:
    - `include_children`: Load and return direct children notes.
    - `include_documents`: Load and return linked documents via NoteDocument.
    - `include_links`: Load and return associated `Link` objects.
    """
    db_note = crud_note.get_note(db, note_id=note_id)
    if db_note is None:
        logger.warning(f"Note with ID {note_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # TODO: Implement eager loading or additional queries for include_* flags
    # if include_children:
    #     db_note.children_data = [child for child in db_note.children] # Requires relationship to be loaded
    # if include_documents:
    #     db_note.documents_data = crud_note_document.get_documents_for_note(db, note_id)
    # if include_links:
    #    db_note.links_data = crud_link.get_links_for_note(db, note_id)

    logger.info(f"Retrieved note ID: {db_note.id}, Title: '{db_note.title}'")
    return db_note

@router.put(
    "/{note_id}",
    response_model=schemas.note.NoteResponse,
    summary="Update a Note",
    description="Modifies an existing note. Only fields present in the request body will be updated.",
)
async def update_note(
    note_id: int,
    note_update: schemas.note.NoteUpdate,
    db: DbDependency,
    # current_user_id: int = Depends(get_current_user_id_or_default) # For ownership check
) -> models.Note:
    """
    Update an existing note.
    - Path parameter `note_id`: ID of the note to update.
    - Request body `note_update`: Fields to update.
    """
    db_note = crud_note.get_note(db, note_id=note_id)
    if db_note is None:
        logger.warning(f"Attempted to update non-existent note with ID: {note_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # Add ownership check here if authentication is implemented
    # if db_note.owner_id != current_user_id: # and not user_is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to update this note")

    try:
        updated_note = crud_note.update_note(db=db, note_id=note_id, note_update=note_update)
        if updated_note is None: # Should not happen if get_note above succeeds, but defensive
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found after update attempt")
        logger.info(f"Note ID: {updated_note.id} updated successfully.")
        return updated_note
    except ValueError as ve: # Catch specific errors like new owner not found
        logger.error(f"ValueError during note update for ID {note_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Could not update note ID {note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update note.")


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Note",
    description="Removes a note from the knowledge base. Consider cascading effects on child notes or links.",
)
async def delete_note(
    note_id: int,
    db: DbDependency,
    # current_user_id: int = Depends(get_current_user_id_or_default) # For ownership check
):
    """
    Delete a note by ID.
    - Path parameter `note_id`: ID of the note to delete.
    """
    db_note_to_delete = crud_note.get_note(db, note_id=note_id)
    if db_note_to_delete is None:
        logger.warning(f"Attempted to delete non-existent note with ID: {note_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found")

    # Add ownership check here
    # if db_note_to_delete.owner_id != current_user_id: # and not user_is_admin:
    #     raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Not authorized to delete this note")

    try:
        deleted_note = crud_note.delete_note(db, note_id=note_id)
        if deleted_note is None: # Should not happen if get_note above succeeds
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Note not found during delete")
        logger.info(f"Note ID: {note_id} deleted successfully.")
        # No content to return for 204
    except Exception as e:
        logger.exception(f"Could not delete note ID {note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete note.")

# Placeholder for GET /{note_id}/tree
# @router.get(
#     "/{note_id}/tree",
#     response_model=YourCustomNoteTreeSchema, # You'll need to define this schema
#     summary="Get Note and its full descendant tree",
# )
# async def get_note_tree(note_id: int, db: DbDependency):
#     # Implementation requires a recursive CRUD function
#     pass