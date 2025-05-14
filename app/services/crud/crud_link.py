# app/services/crud/crud_link.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import or_  # For OR conditions in queries
from typing import Optional, List

from app import models  # Your SQLAlchemy models
from app import schemas  # Your Pydantic schemas
from pydantic import HttpUrl  # Import HttpUrl to check its instance

def get_link(db: Session, link_id: int) -> Optional[models.Link]:
    """
    Retrieve a link by its ID.
    """
    return db.query(models.Link).filter(models.Link.id == link_id).first()

def get_all_links(db: Session, skip: int = 0, limit: int = 100) -> List[models.Link]:
    """
    Retrieve all links with pagination.
    """
    return db.query(models.Link).offset(skip).limit(limit).all()

def create_link(db: Session, link_in: schemas.link.LinkCreate) -> models.Link:
    """
    Create a new link.
    A link can be between two notes (source_id and destination_id)
    or a note to an external URL (source_id and url, with is_web_link=True).
    Or a note might have a primary external link (Note.link_id refers to this Link.id, where this Link has a URL).
    """
    # Basic validation for link integrity
    if link_in.is_web_link and not link_in.url:
        raise ValueError("Web link must have a URL.")
    # If it's not a web link, and it doesn't have a source/destination pair, AND it also doesn't have a URL
    # (meaning it's an internal link trying to be just a placeholder, or a misconfigured link), raise error.
    # This allows a link to be JUST a URL (is_web_link=True, no source/dest) for Note.link_id.
    if not link_in.is_web_link and not (link_in.source_id and link_in.destination_id) and not link_in.url:
        raise ValueError("Internal link must have source and destination notes, or if it's a general link, it should have a URL and be marked as a web link.")


    # Ensure source/destination notes exist if IDs are provided
    if link_in.source_id:
        source_note = db.query(models.Note).filter(models.Note.id == link_in.source_id).first()
        if not source_note:
            raise ValueError(f"Source note with ID {link_in.source_id} not found.")
    if link_in.destination_id:
        destination_note = db.query(models.Note).filter(models.Note.id == link_in.destination_id).first()
        if not destination_note:
            raise ValueError(f"Destination note with ID {link_in.destination_id} not found.")

    # --- FIX: Convert HttpUrl to string before creating DB model ---
    url_to_store: Optional[str] = None
    if link_in.url is not None:
        if isinstance(link_in.url, HttpUrl):  # Check if it's an HttpUrl object
            url_to_store = str(link_in.url)   # Convert to string
        else:
            url_to_store = link_in.url        # Assume it's already a string if not HttpUrl
    # --- End FIX ---

    db_link = models.Link(
        link_type=link_in.link_type,
        destination_id=link_in.destination_id,
        source_id=link_in.source_id,
        url=url_to_store,  # Use the string version
        is_web_link=link_in.is_web_link,
        version=0  # Initial version
    )

    db.add(db_link)
    try:
        db.commit()
        db.refresh(db_link)
    except IntegrityError:
        db.rollback()
        raise
    return db_link

def update_link(
    db: Session,
    link_id: int,
    link_update: schemas.link.LinkUpdate
) -> Optional[models.Link]:
    """
    Update an existing link.
    """
    db_link = get_link(db, link_id)
    if not db_link:
        return None

    update_data = link_update.model_dump(exclude_unset=True)

    # --- FIX: Convert HttpUrl to string if 'url' is being updated ---
    if "url" in update_data and update_data["url"] is not None:
        if isinstance(update_data["url"], HttpUrl):
            update_data["url"] = str(update_data["url"]) # Convert to string
    # --- End FIX ---


    # Validate if source/destination notes exist if they are being updated
    if "source_id" in update_data and update_data["source_id"] is not None:
        source_note = db.query(models.Note).filter(models.Note.id == update_data["source_id"]).first()
        if not source_note:
            raise ValueError(f"Updated source note with ID {update_data['source_id']} not found.")
    if "destination_id" in update_data and update_data["destination_id"] is not None:
        destination_note = db.query(models.Note).filter(models.Note.id == update_data["destination_id"]).first()
        if not destination_note:
            raise ValueError(f"Updated destination note with ID {update_data['destination_id']} not found.")

    for key, value in update_data.items():
        setattr(db_link, key, value)

    # Re-check consistency if is_web_link or url was part of the update
    if "is_web_link" in update_data or ("url" in update_data and update_data["url"] is not None):
        if db_link.is_web_link and not db_link.url:
            # This state should ideally be prevented by schema or earlier logic,
            # but good to catch if update leads to inconsistency.
            raise ValueError("Cannot set as web link without a URL after update.")

    db_link.version = (db_link.version or 0) + 1
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def delete_link(db: Session, link_id: int) -> Optional[models.Link]:
    """
    Delete a link.
    Note: The endpoint calling this should handle nullifying Note.link_id if necessary.
    """
    db_link = get_link(db, link_id)
    if not db_link:
        return None

    # The logic to nullify Note.link_id is better handled in the API endpoint layer
    # just before calling this, as it involves querying another table (Note).
    # This CRUD function focuses solely on the Link entity.

    db.delete(db_link)
    db.commit()
    return db_link

def get_links_for_note(db: Session, note_id: int) -> List[models.Link]:
    """
    Retrieve all links where the given note_id is either the source or the destination.
    This does NOT include the link if it's only referenced by note.link_id.
    The API endpoint combines this with a check for note.link_id.
    """
    return db.query(models.Link).filter(
        or_(models.Link.source_id == note_id, models.Link.destination_id == note_id)
    ).all()

def get_outgoing_links_from_note(db: Session, note_id: int) -> List[models.Link]:
    """
    Retrieve all links originating from the given note_id (note is the source).
    """
    return db.query(models.Link).filter(models.Link.source_id == note_id).all()

def get_incoming_links_to_note(db: Session, note_id: int) -> List[models.Link]:
    """
    Retrieve all links pointing to the given note_id (note is the destination).
    """
    return db.query(models.Link).filter(models.Link.destination_id == note_id).all()