# app/services/crud/crud_link.py

from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from sqlalchemy.sql import or_ # For OR conditions in queries
from typing import Optional, List

from app import models # Your SQLAlchemy models
from app import schemas # Your Pydantic schemas

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

def create_link(db: Session, link_in: schemas.LinkCreate) -> models.Link:
    """
    Create a new link.
    A link can be between two notes (source_id and destination_id)
    or a note to an external URL (source_id and url, with is_web_link=True).
    Or a note might have a primary external link (Note.link_id refers to this Link.id, where this Link has a URL).
    """
    # Basic validation
    if link_in.is_web_link and not link_in.url:
        raise ValueError("Web link must have a URL.")
    if not link_in.is_web_link and not (link_in.source_id and link_in.destination_id):
        # This validation might be too strict if a link can be just a URL associated with a note via Note.link_id
        # without an explicit source_id here. Re-evaluate based on usage.
        # For now, assuming internal links need both source and destination.
        # pass # Allow a link to be just a URL (e.g. for Note.link_id)
        if not link_in.source_id and not link_in.destination_id and not link_in.url:
             raise ValueError("Link must have source/destination notes or a URL.")

    # Ensure source/destination notes exist if IDs are provided
    if link_in.source_id:
        source_note = db.query(models.Note).filter(models.Note.id == link_in.source_id).first()
        if not source_note:
            raise ValueError(f"Source note with ID {link_in.source_id} not found.")
    if link_in.destination_id:
        destination_note = db.query(models.Note).filter(models.Note.id == link_in.destination_id).first()
        if not destination_note:
            raise ValueError(f"Destination note with ID {link_in.destination_id} not found.")

    db_link = models.Link(
        link_type=link_in.link_type,
        destination_id=link_in.destination_id,
        source_id=link_in.source_id,
        url=link_in.url,
        is_web_link=link_in.is_web_link,
        version=0 # Or initial version logic
    )
    # If version is part of LinkCreate schema and optional, handle it:
    # version = link_in.version if link_in.version is not None else 0
    # db_link.version = version

    db.add(db_link)
    try:
        db.commit()
        db.refresh(db_link)
    except IntegrityError:
        db.rollback()
        # Could be due to FK constraints if notes were deleted concurrently.
        raise
    return db_link

def update_link(
    db: Session,
    link_id: int,
    link_update: schemas.LinkUpdate # Assuming you create a LinkUpdate schema
) -> Optional[models.Link]:
    """
    Update an existing link.
    (Requires a LinkUpdate Pydantic schema)
    """
    db_link = get_link(db, link_id)
    if not db_link:
        return None

    update_data = link_update.model_dump(exclude_unset=True)

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

    # If is_web_link is changed, ensure URL presence/absence is consistent
    if "is_web_link" in update_data:
        if db_link.is_web_link and not db_link.url:
            raise ValueError("Cannot set as web link without a URL.")
        # if not db_link.is_web_link and db_link.url: # This might be valid if a note-to-note link also has an associated URL.
        #     db_link.url = None # Or handle based on rules

    db_link.version = (db_link.version or 0) + 1
    db.add(db_link)
    db.commit()
    db.refresh(db_link)
    return db_link

def delete_link(db: Session, link_id: int) -> Optional[models.Link]:
    """
    Delete a link.
    (Consider implications: if a Note.link_id points here, it might need to be nullified)
    """
    db_link = get_link(db, link_id)
    if not db_link:
        return None

    # If any notes directly reference this link via Note.link_id,
    # you might want to set those foreign keys to NULL.
    # db.query(models.Note).filter(models.Note.link_id == link_id).update({"link_id": None})

    db.delete(db_link)
    db.commit()
    return db_link

def get_links_for_note(db: Session, note_id: int) -> List[models.Link]:
    """
    Retrieve all links where the given note_id is either the source or the destination.
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