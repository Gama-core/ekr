# app/features/semantic_retrieval/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status, Depends
from sqlalchemy.orm import Session  # For DB session dependency
from typing import List, Optional

# Core and DB connector imports
from app.core.database import get_db  # To get DB session for certain operations

# Feature specific imports
from app.features.semantic_retrieval import index_service, retrieval_service
from app.features.semantic_retrieval.schemas import (
    RetrieveRequest, RetrieveResponse,
    IndexSingleNoteRequest, IndexNoteByIdRequest, IndexBatchNotesRequest, IndexOperationResponse,
    DeleteFromIndexRequest,
    IndexStatsResponse, RebuildStatusResponse
)
# Assuming NoteForIndex and NoteReaderService are for fetching note data from DB
from app.db_connectors.note_reader_service import get_note_by_id_for_indexing
from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Retrieval Endpoint ---
@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    summary="Retrieve Relevant Context (RAG)",
    description="Given a query, retrieves the most semantically relevant text chunks from the indexed knowledge base.",
)
async def retrieve_context_endpoint(request: RetrieveRequest):
    try:
        items, message = await retrieval_service.retrieve_relevant_context(
            query_text=request.query,
            top_k_override=request.top_k
        )
        return RetrieveResponse(query_echo=request.query, retrieved_items=items, message=message)
    except Exception as e:
        logger.exception(f"Unexpected error in /retrieve endpoint for query '{request.query[:50]}...': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Error retrieving context.")


# --- Index Management Endpoints ---

@router.post(
    "/index/note/by-id",
    response_model=IndexOperationResponse,
    summary="Index a Single Note by ID",
    description="Fetches a note by its ID from the database and adds/updates it in the vector index.",
    status_code=status.HTTP_201_CREATED,
)
async def index_note_by_id_endpoint(
        request: IndexNoteByIdRequest,
        db: Session = Depends(get_db)
):
    note_to_index: Optional[DBNoteForIndexSchema] = await get_note_by_id_for_indexing(db, request.note_id)
    if not note_to_index:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Note with ID {request.note_id} not found in database.")

    try:
        success, message, doc_id = index_service.add_note_to_index(note_to_index)
        response_status = "success" if success else "failed"
        http_status = status.HTTP_201_CREATED if success else status.HTTP_500_INTERNAL_SERVER_ERROR

        if not success:  # Raise if service indicated failure
            raise HTTPException(status_code=http_status, detail=message)

        return IndexOperationResponse(status=response_status, note_id=request.note_id, doc_id=doc_id, message=message)
    except Exception as e:
        logger.exception(f"Error indexing note ID {request.note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Failed to index note: {str(e)}")


@router.post(
    "/index/note/direct",
    response_model=IndexOperationResponse,
    summary="Index a Single Note with Provided Data",
    description="Adds/updates a note in the vector index using the provided note data.",
    status_code=status.HTTP_201_CREATED,
)
async def index_note_direct_endpoint(request: IndexSingleNoteRequest):
    try:
        # Ensure the input conforms to DBNoteForIndexSchema if there are subtle differences,
        # or adjust IndexSingleNoteRequest.note to be exactly DBNoteForIndexSchema.
        # For now, assuming request.note is already compatible.
        note_data_to_index: DBNoteForIndexSchema = request.note

        success, message, doc_id = index_service.add_note_to_index(note_data_to_index)
        response_status = "success" if success else "failed"
        http_status = status.HTTP_201_CREATED if success else status.HTTP_500_INTERNAL_SERVER_ERROR

        if not success:
            raise HTTPException(status_code=http_status, detail=message)

        return IndexOperationResponse(status=response_status, note_id=note_data_to_index.id, doc_id=doc_id,
                                      message=message)
    except Exception as e:
        logger.exception(f"Error indexing note directly (ID: {request.note.id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to index note directly: {str(e)}")


@router.delete(
    "/index/note/{note_id}",
    response_model=IndexOperationResponse,
    summary="Delete a Note from Index",
    description="Removes a note and its associated chunks from the vector index by its original database ID.",
)
async def delete_note_from_index_endpoint(note_id: int):
    try:
        success, message, doc_id = index_service.delete_note_from_index(note_id)
        response_status = "success" if success else "failed"  # or "not_found" if applicable from service

        if not success and "not found" not in message.lower() and "not have been indexed" not in message.lower():  # if actual failure
            raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
        if not success and (
                "not found" in message.lower() or "not have been indexed" in message.lower()):  # if it wasn't there to begin with
            # Still return 200 or 204, but indicate it in message
            return IndexOperationResponse(status="not_found", note_id=note_id, doc_id=doc_id, message=message)

        return IndexOperationResponse(status=response_status, note_id=note_id, doc_id=doc_id, message=message)
    except Exception as e:
        logger.exception(f"Error deleting note ID {note_id} from index: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to delete note from index: {str(e)}")


@router.get(
    "/index/stats",
    response_model=IndexStatsResponse,
    summary="Get Index Statistics",
    description="Retrieves statistics about the current vector index, such as the total number of indexed vectors.",
)
async def get_index_stats_endpoint():
    try:
        count, message = index_service.get_index_statistics()
        if "Error" in message or "not available" in message:  # Check if service indicated an error
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
        return IndexStatsResponse(total_indexed_vectors=count, message=message)
    except Exception as e:
        logger.exception(f"Error getting index statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail="Failed to retrieve index statistics.")


@router.post(
    "/index/rebuild",
    response_model=RebuildStatusResponse,
    summary="Trigger Full Index Rebuild",
    description="Triggers a full rebuild of the vector index from all notes in the database. This can be a long operation.",
    status_code=status.HTTP_202_ACCEPTED  # Accepted, as it's a long process
)
async def rebuild_index_endpoint(db: Session = Depends(get_db)):
    # Note: For a true long-running task, use BackgroundTasks.
    # For now, this will block until completion if build_full_index is fully synchronous.
    # If build_full_index becomes async, this endpoint can await it.
    logger.info("Full index rebuild endpoint triggered.")
    try:
        # This is a synchronous call as implemented in index_service.
        # If it's very long, use FastAPI's BackgroundTasks.
        notes_processed, vectors_added = await index_service.build_full_index(db, force_rebuild=True)
        message = f"Index rebuild completed. Notes processed: {notes_processed}. Total vectors in index: {vectors_added}."
        logger.info(message)
        return RebuildStatusResponse(status="completed", message=message, notes_processed=notes_processed,
                                     vectors_added=vectors_added)
    except Exception as e:
        logger.exception("Error during full index rebuild trigger.")
        # Cannot return 500 here as it might have started in background
        # For now, since it's sync, 500 is okay if it fails during the call.
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to complete index rebuild: {str(e)}")