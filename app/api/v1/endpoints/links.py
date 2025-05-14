# app/api/v1/endpoints/links.py
import logging
from typing import List, Optional, Annotated

from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session

from app import schemas, models
from app.services.crud import crud_link, crud_note  # To validate note existence
from app.core.database import get_db

logger = logging.getLogger(__name__)
router = APIRouter()

DbDependency = Annotated[Session, Depends(get_db)]


@router.post(
    "/",
    response_model=schemas.link.LinkResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create a new Link",
    description="Creates a new link, which can be between two notes or from a note to an external URL.",
)
async def create_link(
        link_in: schemas.link.LinkCreate,
        db: DbDependency,
) -> models.Link:
    """
    Create a new link.
    - **link_type**: Optional type of the link.
    - **source_id**: Optional ID of the source Note.
    - **destination_id**: Optional ID of the destination Note.
    - **url**: Optional external URL if `is_web_link` is true.
    - **is_web_link**: Boolean indicating if it's an external web link.
    """
    try:
        # crud_link.create_link already has validation for source/destination notes
        # and for web_link URL presence.
        created_link = crud_link.create_link(db=db, link_in=link_in)
        logger.info(f"Link created with ID: {created_link.id}")
        return created_link
    except ValueError as ve:  # Catch validation errors from CRUD
        logger.error(f"ValueError during link creation: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Could not create link: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not create link.")


@router.get(
    "/notes/{note_id}",
    response_model=List[schemas.link.LinkResponse],
    summary="Get all links associated with a specific Note",
    description="Retrieves all links where the given note is either the source or the destination, or if the note's `link_id` points to one of these links.",
)
async def get_links_for_note_endpoint(  # Renamed to avoid conflict with crud_link.get_links_for_note
        note_id: int,
        db: DbDependency,
) -> List[models.Link]:
    """
    Get all links for a specific note.
    This includes:
    - Links where this note is the `source_id`.
    - Links where this note is the `destination_id`.
    - The link referenced by `note.link_id` (if any).
    """
    note = crud_note.get_note(db, note_id)
    if not note:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Note with ID {note_id} not found.")

    # Get outgoing and incoming links
    associated_links = crud_link.get_links_for_note(db, note_id=note_id)

    # If the note has a primary link_id, fetch that link specifically and add it if not already present
    if note.link_id:
        primary_link = crud_link.get_link(db, note.link_id)
        if primary_link and primary_link not in associated_links:
            # Check to avoid duplicates if get_links_for_note somehow already included it
            # (e.g., if note.link_id pointed to a link where this note was also source/dest)
            is_present = any(link.id == primary_link.id for link in associated_links)
            if not is_present:
                associated_links.append(primary_link)

    logger.info(f"Retrieved {len(associated_links)} links associated with Note ID: {note_id}")
    return associated_links


@router.get(
    "/{link_id}",
    response_model=schemas.link.LinkResponse,
    summary="Get a specific Link by ID",
    description="Retrieves details of a single link by its ID.",
)
async def get_link_by_id(  # Renamed to avoid conflict
        link_id: int,
        db: DbDependency,
) -> models.Link:
    db_link = crud_link.get_link(db, link_id=link_id)
    if db_link is None:
        logger.warning(f"Link with ID {link_id} not found.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")
    logger.info(f"Retrieved Link ID: {link_id}")
    return db_link


@router.put(
    "/{link_id}",
    response_model=schemas.link.LinkResponse,
    summary="Update a Link",
    description="Modifies an existing link. Only fields present in the request body will be updated.",
)
async def update_link(
        link_id: int,
        link_update: schemas.link.LinkUpdate,
        db: DbDependency,
) -> models.Link:
    """
    Update an existing link.
    - Path parameter `link_id`: ID of the link to update.
    - Request body `link_update`: Fields to update.
    """
    db_link = crud_link.get_link(db, link_id=link_id)
    if db_link is None:
        logger.warning(f"Attempted to update non-existent link with ID: {link_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    try:
        updated_link = crud_link.update_link(db=db, link_id=link_id, link_update=link_update)
        if updated_link is None:  # Should not happen if get_link above succeeds
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found after update attempt")
        logger.info(f"Link ID: {updated_link.id} updated successfully.")
        return updated_link
    except ValueError as ve:  # Catch validation errors from CRUD
        logger.error(f"ValueError during link update for ID {link_id}: {ve}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(ve))
    except Exception as e:
        logger.exception(f"Could not update link ID {link_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not update link.")


@router.delete(
    "/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete a Link",
    description="Removes a link. Consider if notes referencing this link via `link_id` should have their `link_id` nullified.",
)
async def delete_link(
        link_id: int,
        db: DbDependency,
):
    """
    Delete a link by ID.
    - Path parameter `link_id`: ID of the link to delete.
    """
    db_link_to_delete = crud_link.get_link(db, link_id=link_id)
    if db_link_to_delete is None:
        logger.warning(f"Attempted to delete non-existent link with ID: {link_id}")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found")

    try:
        # Optional: Before deleting the link, nullify Note.link_id if any notes point to it.
        # This prevents FK constraint errors if the DB has ON DELETE RESTRICT (default)
        # and makes data consistent.
        notes_referencing_this_link = db.query(models.Note).filter(models.Note.link_id == link_id).all()
        if notes_referencing_this_link:
            for note in notes_referencing_this_link:
                note.link_id = None
                logger.info(f"Nullified link_id for Note ID {note.id} which referenced deleted Link ID {link_id}")
            db.commit()  # Commit the nullification

        deleted_link = crud_link.delete_link(db, link_id=link_id)
        if deleted_link is None:  # Should not happen
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Link not found during delete")
        logger.info(f"Link ID: {link_id} deleted successfully.")
        # No content to return for 204
    except Exception as e:
        logger.exception(f"Could not delete link ID {link_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Could not delete link.")