# app/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from typing import Optional

# CHANGED: Use relative imports for modules within the 'app' package
from . import index_service, retrieval_service
from .schemas import (
    RetrieveRequest, RetrieveResponse,
    IndexNoteByIdRequest, IndexOperationResponse,
    IndexStatsResponse, RebuildStatusResponse,
    NoteForIndex as DBNoteForIndexSchema
)
from .clients.database_client import database_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/retrieve", response_model=RetrieveResponse, summary="Retrieve Relevant Context (RAG)")
async def retrieve_context_endpoint(request: RetrieveRequest):
    """Retrieves context for a given user and query from the local vector index."""
    logger.info(f"Endpoint /retrieve: user_id: {request.user_id}, query: '{request.query[:30]}...'")
    try:
        items, message = await retrieval_service.retrieve_relevant_context(
            query_text=request.query,
            user_id=request.user_id,
            top_k_override=request.top_k
        )
        return RetrieveResponse(
            query_echo=request.query,
            user_id_echo=request.user_id,
            retrieved_items=items,
            message=message
        )
    except Exception as e:
        logger.exception(f"Endpoint /retrieve: Error for user {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post(
    "/index/note/by-id",
    response_model=IndexOperationResponse,
    summary="Index a Single Note by ID via Database API",
    status_code=status.HTTP_201_CREATED,
)
async def index_note_by_id_endpoint(request: IndexNoteByIdRequest):
    """Fetches a note by its ID from the database-api and indexes it."""
    logger.info(f"Endpoint /index/note/by-id: note_id: {request.note_id}")

    # Fetch note data from the dedicated database-api service
    note_to_index = await database_client.get_note_by_id(request.note_id)

    if not note_to_index:
        logger.warning(
            f"Note ID {request.note_id} not found via database-api. Attempting removal from index if exists.")
        success, message, doc_id = index_service.delete_note_from_index(request.note_id)
        if success:
            return IndexOperationResponse(
                status="removed_from_index_as_not_in_db",
                note_id=request.note_id,
                doc_id=doc_id,
                message=message
            )
        else:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

    try:
        success, message, doc_id = index_service.add_or_update_note_in_index(note_to_index)
        if not success:
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

        return IndexOperationResponse(
            status="success",
            note_id=request.note_id,
            doc_id=doc_id,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error indexing note ID {request.note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.get("/index/stats", response_model=IndexStatsResponse, summary="Get Detailed Index Statistics")
async def get_index_stats_endpoint():
    """Retrieves detailed statistics about the current vector index and its configuration."""
    logger.info("Endpoint /index/stats called.")
    try:
        stats_dict = index_service.get_index_statistics()
        if "Error" in stats_dict.get("message", "") or "not available" in stats_dict.get("message", ""):
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=stats_dict.get("message", "Service unavailable or index not ready.")
            )
        return IndexStatsResponse(**stats_dict)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


async def _background_rebuild_task(force_rebuild_flag: bool):
    """Helper function to run the index build in the background without db sessions."""
    try:
        logger.info(f"Background task started: Full index rebuild (force_rebuild={force_rebuild_flag}).")
        # The service no longer needs a db session
        notes_processed, total_vectors = await index_service.build_full_index(force_rebuild=force_rebuild_flag)
        logger.info(f"Background task finished. Notes Processed: {notes_processed}, Total Vectors: {total_vectors}")
    except Exception as e_bg:
        logger.exception(f"Background full rebuild task failed: {e_bg}")


@router.post(
    "/index/rebuild",
    response_model=RebuildStatusResponse,
    summary="Trigger Full Index Rebuild",
    status_code=status.HTTP_202_ACCEPTED
)
async def rebuild_full_index_endpoint(background_tasks: BackgroundTasks):
    """Triggers a full rebuild of the vector index from the database-api service."""
    logger.info("Endpoint /index/rebuild: Full index rebuild triggered (force_rebuild=True).")
    # The background task is now simpler and does not need the DB session factory
    background_tasks.add_task(_background_rebuild_task, force_rebuild_flag=True)
    return RebuildStatusResponse(status="accepted", message="Full index rebuild initiated in background.")


@router.delete(
    "/index/note/{note_id}",
    response_model=IndexOperationResponse,
    summary="Delete a Single Note by ID from the Index"
)
async def delete_note_from_index_endpoint(note_id: int):
    """Removes a note and its vectors from the index using its database ID."""
    logger.info(f"Endpoint /index/note/{note_id} (DELETE): Received request.")
    try:
        success, message, doc_id = index_service.delete_note_from_index(note_id)

        status_str = "not_found_in_index" if "not found in index" in message else "deleted"
        if not success:
            status_str = "failed_to_delete"
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)

        return IndexOperationResponse(
            status=status_str,
            note_id=note_id,
            doc_id=doc_id,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error deleting note {note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))