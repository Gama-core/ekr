import logging
from fastapi import APIRouter, HTTPException, Query, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.features.elasticsearch.service import ElasticsearchService
from app.features.elasticsearch.schemas import (
    TicketRequest,
    ReindexResponse,
    DeleteResponse,
    NoteSearchHit
)
from app.core.database import get_db
from app.db_connectors.models import Note

logger = logging.getLogger(__name__)
router = APIRouter()
es_service = ElasticsearchService()

#  SEARCH ENDPOINT — Full-text search (currently not user-filtered)
@router.get(
    "/search",
    response_model=List[NoteSearchHit],
    summary="Search Notes",
    description="Search notes by keyword in Elasticsearch (title or text).",
    tags=["V1 - Elasticsearch"]
)
def search_notes_endpoint(q: str = Query(..., min_length=1, description="Search query string.")):
    if not es_service.es:
        logger.error("Elasticsearch not available for /search.")
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable.")
    try:
        return es_service.search_notes(query=q)
    except Exception as e:
        logger.exception(f"Search error for query '{q}': {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during search.")

#  REINDEX ENDPOINT — Manually reindex a note by ID
@router.post(
    "/notes/{note_id}/reindex",
    response_model=ReindexResponse,
    summary="Reindex a Note",
    description="Reindex a single note by ID into Elasticsearch.",
    tags=["V1 - Elasticsearch"]
)
def reindex_note_endpoint(note_id: int, db: Session = Depends(get_db)):
    if not es_service.es:
        logger.error(f"Elasticsearch unavailable for note {note_id}.")
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable.")
    try:
        success = es_service.index_note(db, note_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Note {note_id} could not be reindexed.")
        return ReindexResponse(message=f"Note {note_id} reindexed successfully.", status=True)
    except Exception as e:
        logger.exception(f"Error reindexing note {note_id}: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error reindexing note.")

#  DELETE ENDPOINT — Remove a note from Elasticsearch
@router.delete(
    "/notes/{note_id}",
    response_model=DeleteResponse,
    summary="Delete Note from Elasticsearch",
    description="Delete a note from Elasticsearch by ID.",
    tags=["V1 - Elasticsearch"]
)
def delete_note_from_es_endpoint(note_id: int):
    if not es_service.es:
        logger.error(f"Elasticsearch unavailable for deletion of note {note_id}.")
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable.")
    try:
        success = es_service.delete_note(note_id=note_id)
        if not success:
            raise HTTPException(status_code=404, detail=f"Note {note_id} could not be deleted.")
        return DeleteResponse(message=f"Note {note_id} deleted from Elasticsearch.")
    except Exception as e:
        logger.exception(f"Error deleting note {note_id}: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error deleting note.")

#  TICKET ENDPOINT — Index via ticket, with note ownership enforced (auth placeholder)
@router.post(
    "/ticket",
    response_model=ReindexResponse,
    summary="Index Note via Ticket",
    description="Receive a note ID and index it if it exists and is valid.",
    tags=["V1 - Elasticsearch"]
)
def receive_index_ticket_endpoint(ticket: TicketRequest, db: Session = Depends(get_db)):
    if not es_service.es:
        logger.error(f"Elasticsearch unavailable for ticket on note {ticket.note_id}.")
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable.")

    # Placeholder: Add user validation/orchestration check here later
    note = db.query(Note).filter(Note.id == ticket.note_id).first()
    if not note:
        raise HTTPException(status_code=404, detail="Note not found.")

    try:
        success = es_service.index_note(db, note.id)
        if not success:
            raise HTTPException(status_code=400, detail="Failed to index note.")
        return ReindexResponse(message=f"Note {note.id} indexed successfully.", status=True)
    except Exception as e:
        logger.exception(f"Ticket indexing error for note {ticket.note_id}: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error indexing note.")

#  MAINTENANCE ENDPOINT — Repair index for all unindexed notes (orchestrator-only)
@router.post(
    "/maintenance/repair-index",
    summary="Repair Elasticsearch Index (Maintenance)",
    description="Scan DB and reindex missing notes into Elasticsearch. Orchestrator-managed.",
    tags=["Maintenance"]
)
def repair_elasticsearch_index(db: Session = Depends(get_db)):
    if not es_service.es:
        raise HTTPException(status_code=503, detail="Elasticsearch unavailable.")

    try:
        repaired_count = es_service.repair_index(db)
        return {"message": f"Repair completed. {repaired_count} notes reindexed."}
    except Exception as e:
        logger.exception(f"Repair index operation failed: {e}")
        raise HTTPException(status_code=500, detail="Unexpected error during repair.")
