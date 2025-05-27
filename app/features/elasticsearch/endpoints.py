# app/features/elasticsearch/endpoints.py
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
# Corrected import based on your previous request
from app.core.database import get_db # Ensure 'database.py' exists in app/core/ and has get_db

logger = logging.getLogger(__name__)
router = APIRouter() # Router for Elasticsearch feature endpoints

# Instantiate the service.
# For features requiring more complex lifecycle or state, consider FastAPI Depends.
es_service = ElasticsearchService()

@router.get(
    "/search",
    response_model=List[NoteSearchHit],
    summary="Search Notes",
    description="Search notes by keyword in Elasticsearch (title or text).",
    tags=["V1 - Elasticsearch"]
)
def search_notes_endpoint(q: str = Query(..., min_length=1, description="Search query string.")):
    if not es_service.es: # Check if ES client is available
        logger.error("Elasticsearch service not available for /search endpoint.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Elasticsearch service is currently unavailable."
        )
    try:
        results = es_service.search_notes(query=q)
        return results
    except Exception as e: # Catch any other unexpected errors
        logger.exception(f"Unexpected error in /search endpoint for query '{q}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="An unexpected error occurred during search.")

@router.post(
    "/notes/{note_id}/reindex",
    response_model=ReindexResponse,
    summary="Reindex a Note",
    description="Reindex a single note by ID into Elasticsearch.",
    tags=["V1 - Elasticsearch"]
)
def reindex_note_endpoint(note_id: int, db: Session = Depends(get_db)):
    if not es_service.es:
        logger.error(f"Elasticsearch service not available for reindexing note {note_id}.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Elasticsearch service is currently unavailable."
        )
    try:
        success = es_service.index_note(db, note_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to reindex note {note_id}. It might not exist or an indexing error occurred."
            )
        return ReindexResponse(message=f"Note {note_id} reindexed successfully.", status=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error reindexing note {note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error reindexing note {note_id}.")

@router.delete(
    "/notes/{note_id}",
    response_model=DeleteResponse,
    summary="Delete Note from Elasticsearch",
    description="Delete a note from Elasticsearch by ID.",
    tags=["V1 - Elasticsearch"]
)
def delete_note_from_es_endpoint(note_id: int):
    if not es_service.es:
        logger.error(f"Elasticsearch service not available for deleting note {note_id}.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Elasticsearch service is currently unavailable."
        )
    try:
        success = es_service.delete_note(note_id=note_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Failed to delete note {note_id} from Elasticsearch. It might not exist or a deletion error occurred."
            )
        return DeleteResponse(message=f"Note {note_id} processed for deletion from Elasticsearch.")
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error deleting note {note_id} from Elasticsearch: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error deleting note {note_id}.")

@router.post(
    "/ticket",
    response_model=ReindexResponse,
    summary="Index Note via Ticket",
    description="Receive a note ID via webhook-style ticket and index it into Elasticsearch.",
    tags=["V1 - Elasticsearch"]
)
def receive_index_ticket_endpoint(ticket: TicketRequest, db: Session = Depends(get_db)):
    if not es_service.es:
        logger.error(f"Elasticsearch service not available for processing ticket for note {ticket.note_id}.")
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Elasticsearch service is currently unavailable."
        )
    try:
        success = es_service.index_note(db, ticket.note_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to index note {ticket.note_id} via ticket. Note might not exist or an indexing error occurred."
            )
        return ReindexResponse(message=f"Note {ticket.note_id} indexed successfully via ticket.", status=True)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error processing ticket for note {ticket.note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Unexpected error processing ticket for note {ticket.note_id}.")