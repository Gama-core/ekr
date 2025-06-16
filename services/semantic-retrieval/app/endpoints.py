# app/features/semantic_retrieval/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional

from app.core.database import get_db, SessionLocal as AppSessionLocal
from app.features.semantic_retrieval import index_service, retrieval_service
from app.features.semantic_retrieval.schemas import (
    RetrieveRequest, RetrieveResponse,
    IndexNoteByIdRequest, IndexOperationResponse,
    IndexStatsResponse, RebuildStatusResponse
)
from app.db_connectors.note_reader_service import get_note_by_id_for_indexing
from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    summary="Retrieve Relevant Context (RAG) for a User",
)
async def retrieve_context_endpoint(request: RetrieveRequest):
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
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error retrieving context: {str(e)}")


@router.post(
    "/index/note/by-id",
    response_model=IndexOperationResponse,
    summary="Index a Single Note by ID",
    description="Fetches a note by its ID from the database and adds or updates it in the vector index. Uses IndexIDMap for vector management.",
    status_code=status.HTTP_201_CREATED,
)
async def index_note_by_id_endpoint(
        request: IndexNoteByIdRequest,
        db: Session = Depends(get_db)
):
    logger.info(f"Endpoint /index/note/by-id: note_id: {request.note_id}")
    note_to_index: Optional[DBNoteForIndexSchema] = await get_note_by_id_for_indexing(db, request.note_id)

    if not note_to_index:
        # If the note is not found in the DB, it implies it might have been deleted.
        # We should ensure it's also removed from the index if it existed there.
        logger.warning(
            f"Endpoint /index/note/by-id: Note with ID {request.note_id} not found in database. Attempting removal from index if it exists.")
        doc_id_to_remove = f"note_{request.note_id}"

        index_instance = index_service.get_global_vector_index()  # Get current index
        if index_instance and index_instance.docstore.document_exists(doc_id_to_remove):
            from app.features.semantic_retrieval.llama_ops.indexing_ops import remove_document_from_index
            from app.features.semantic_retrieval.llama_ops.index_io import persist_index_and_vector_store

            removal_success = remove_document_from_index(index_instance, doc_id_to_remove)
            vector_store_instance = index_service.get_global_faiss_vector_store()

            if removal_success and index_instance and vector_store_instance:
                persist_index_and_vector_store(index_instance, vector_store_instance)
                message = f"Note ID {request.note_id} not found in DB and successfully removed from index."
                logger.info(message)
                return IndexOperationResponse(status="removed_from_index_as_not_in_db", note_id=request.note_id,
                                              doc_id=doc_id_to_remove, message=message)
            else:
                message = f"Note ID {request.note_id} not found in DB; failed to remove from index or index unavailable."
                logger.error(message)
                # Not a 404 for the endpoint, as the operation was to "sync" the index state.
                # This is more of a processing issue.
                raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=message)
        else:
            # Note not in DB and not in index, so it's a clean "not found" for indexing purposes.
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f"Note with ID {request.note_id} not found in database and not in index.")

    try:
        success, message, doc_id = index_service.add_or_update_note_in_index(note_to_index)
        response_status_str = "success" if success else "failed"
        http_status_code = status.HTTP_201_CREATED if success else status.HTTP_500_INTERNAL_SERVER_ERROR

        if not success:
            raise HTTPException(status_code=http_status_code, detail=message)

        return IndexOperationResponse(status=response_status_str, note_id=request.note_id, doc_id=doc_id,
                                      message=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Endpoint /index/note/by-id: Error indexing note ID {request.note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to index note by ID: {str(e)}")


@router.get(
    "/index/stats",
    response_model=IndexStatsResponse,
    summary="Get Detailed Index Statistics",  # Updated summary
    description="Retrieves detailed statistics about the current vector index, configuration, and LlamaIndex settings.",
    # Updated description
)
async def get_index_stats_endpoint():
    logger.info("Endpoint /index/stats called.")
    try:
        stats_dict = index_service.get_index_statistics()

        # Check if the message indicates an error state before trying to construct the full response
        if "Error" in stats_dict.get("message", "") or \
                "not available" in stats_dict.get("message", "") or \
                "not fully initialized" in stats_dict.get("message", ""):
            # If only basic error info is available, return that within the schema structure
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=stats_dict.get("message", "Service unavailable or index not ready.")
            )

        # If we have full stats, construct the response
        return IndexStatsResponse(**stats_dict)

    except HTTPException:  # Re-raise HTTPExceptions directly
        raise
    except Exception as e:
        logger.exception(f"Endpoint /index/stats: Error getting statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to retrieve index statistics: {str(e)}")


async def _background_rebuild_task(db_session_factory, force_rebuild_flag: bool):
    db_bg = db_session_factory()
    try:
        logger.info(f"Background task started: Full index rebuild (force_rebuild={force_rebuild_flag}).")
        notes_processed, total_vectors = await index_service.build_full_index(db_bg, force_rebuild=force_rebuild_flag)
        logger.info(
            f"Background task finished for full rebuild. DB Notes Processed: {notes_processed}, Total Vectors in FAISS (IndexIDMap): {total_vectors}")
    except Exception as e_bg:
        logger.exception(f"Background full rebuild task failed: {e_bg}")
    finally:
        db_bg.close()


@router.post(
    "/index/rebuild",
    response_model=RebuildStatusResponse,
    summary="Trigger Full Index Rebuild (All Users)",
    description="Triggers a full rebuild of the vector index from all notes in the database. Uses IndexIDMap. Accepted for background processing.",
    status_code=status.HTTP_202_ACCEPTED
)
async def rebuild_full_index_endpoint(background_tasks: BackgroundTasks):
    logger.info(
        "Endpoint /index/rebuild: Full index rebuild triggered. Task (force_rebuild=True) will run in background.")
    # For a full rebuild, always force it to ensure clean state.
    background_tasks.add_task(_background_rebuild_task, AppSessionLocal, force_rebuild_flag=True)
    return RebuildStatusResponse(status="accepted",
                                 message="Full index rebuild process accepted (force_rebuild=True) and initiated in background.")


@router.delete(
    "/index/note/{note_id}",
    response_model=IndexOperationResponse,
    summary="Delete a Single Note by ID from the Index",
    description="Removes a note and its associated vectors from the vector index using its original database ID.",
    status_code=status.HTTP_200_OK,  # Or HTTP_204_NO_CONTENT if no body is returned on success
)
async def delete_note_from_index_endpoint(
        note_id: int,
        # db: Session = Depends(get_db) # Not strictly needed if we only operate on the index
):
    logger.info(f"Endpoint /index/note/{note_id} (DELETE): Received request.")

    try:
        success, message, doc_id = index_service.delete_note_from_index(note_id)

        response_status_str = "deleted" if success else "failed_to_delete"
        if success and "not found in index" in message:  # Handle idempotent case
            response_status_str = "not_found_in_index"
            # For not found, a 200 is fine, or you could choose 404 if you prefer strict "resource not found"
            # For consistency with add/update, 200 with a specific status message is okay.

        http_status_code = status.HTTP_200_OK
        if not success and response_status_str == "failed_to_delete":
            http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
            # Raise HTTPException for clear error reporting if desired
            raise HTTPException(status_code=http_status_code, detail=message)

        return IndexOperationResponse(
            status=response_status_str,
            note_id=note_id,
            doc_id=doc_id,  # doc_id will be f"note_{note_id}"
            message=message
        )
    except HTTPException:  # Re-raise if already an HTTPException
        raise
    except Exception as e:
        logger.exception(f"Endpoint /index/note/{note_id} (DELETE): Error deleting note: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to delete note from index: {str(e)}")