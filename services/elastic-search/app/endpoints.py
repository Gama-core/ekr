# /elastic-search/app/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, Query, Depends, status
from typing import List
from .service import ElasticsearchService
from .schemas import TicketRequest, ReindexResponse, DeleteResponse, NoteSearchHit

logger = logging.getLogger(__name__)
router = APIRouter()
es_service = ElasticsearchService()

async def get_es_service() -> ElasticsearchService:
    if not await es_service._check_client():
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Search service unavailable.")
    return es_service

# All endpoints below will now be grouped under a single "Elasticsearch" tag
TAG_NAME = "Elasticsearch"

@router.get("/search", response_model=List[NoteSearchHit], summary="Search Notes", tags=[TAG_NAME])
async def search_notes_endpoint(q: str = Query(...), service: ElasticsearchService = Depends(get_es_service)):
    return await service.search_notes(query=q)

@router.post("/notes/{note_id}/reindex", response_model=ReindexResponse, summary="Reindex a Note", tags=[TAG_NAME])
async def reindex_note_endpoint(note_id: int, service: ElasticsearchService = Depends(get_es_service)):
    if not await service.index_note(note_id):
        raise HTTPException(status_code=404, detail="Note not found or failed to index.")
    return ReindexResponse(message=f"Note {note_id} reindexed.", status=True)

# --- THIS IS THE MISSING BLOCK ---
@router.delete("/notes/{note_id}", response_model=DeleteResponse, summary="Delete Note from Elasticsearch", tags=[TAG_NAME])
async def delete_note_from_es_endpoint(note_id: int, service: ElasticsearchService = Depends(get_es_service)):
    """Deletes a single note from the Elasticsearch index by its ID."""
    await service.delete_note(note_id=note_id)
    return DeleteResponse(message=f"Note {note_id} removed from search index.")
# --- END OF MISSING BLOCK ---

@router.post("/ticket", response_model=ReindexResponse, summary="Index Note via Ticket", tags=[TAG_NAME])
async def receive_index_ticket_endpoint(ticket: TicketRequest, service: ElasticsearchService = Depends(get_es_service)):
    if not await service.index_note(ticket.note_id):
        raise HTTPException(status_code=404, detail="Note not found or failed to index.")
    return ReindexResponse(message=f"Note {ticket.note_id} indexed.", status=True)

# This endpoint has its own separate tag
@router.post("/maintenance/repair-index", summary="Repair Elasticsearch Index", tags=["Maintenance"])
async def repair_elasticsearch_index(service: ElasticsearchService = Depends(get_es_service)):
    count = await service.repair_index()
    return {"message": f"Repair complete. {count} notes reindexed."}