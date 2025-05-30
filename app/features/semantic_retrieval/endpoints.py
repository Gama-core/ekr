# app/features/semantic_retrieval/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.database import get_db, SessionLocal as AppSessionLocal  # For background tasks

from app.features.semantic_retrieval import index_service, retrieval_service
from app.features.semantic_retrieval.schemas import (
    RetrieveRequest, RetrieveResponse,
    IndexSingleNoteRequest, IndexNoteByIdRequest, IndexOperationResponse,
    UserNotesIndexOperationResponse,  # Added this
    IndexStatsResponse, RebuildStatusResponse
)

from app.db_connectors.note_reader_service import get_note_by_id_for_indexing
from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema

logger = logging.getLogger(__name__)
router = APIRouter()


# --- Retrieval Endpoint ---
@router.post(
    "/retrieve",
    response_model=RetrieveResponse,
    summary="Retrieve Relevant Context (RAG) for a User",
    description="Given a query and user_id, retrieves semantically relevant text chunks, filtered for the specified user and excluding logically deleted items.",
)
async def retrieve_context_endpoint(request: RetrieveRequest):
    # TODO: Secure this. Authenticate user and ensure 'request.user_id' matches authenticated user or an admin.
    logger.info(f"Retrieval request for user_id: {request.user_id}, query: '{request.query[:30]}...'")
    try:
        items, message = await retrieval_service.retrieve_relevant_context(
            query_text=request.query,
            user_id=request.user_id,  # Pass user_id to the service
            top_k_override=request.top_k
        )
        return RetrieveResponse(
            query_echo=request.query,
            user_id_echo=request.user_id,  # Echo back the user_id
            retrieved_items=items,
            message=message
        )
    except Exception as e:
        logger.exception(
            f"Unexpected error in /retrieve endpoint for query '{request.query[:50]}...' by user {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Error retrieving context: {str(e)}")


# --- Index Management Endpoints ---

@router.post(
    "/index/note/by-id",
    response_model=IndexOperationResponse,
    summary="Index a Single Note by ID",
    description="Fetches a note by its ID from the database and adds/updates it in the vector index (DocStore updated, new vectors added to FAISS).",
    status_code=status.HTTP_201_CREATED,
)
async def index_note_by_id_endpoint(
        request: IndexNoteByIdRequest,
        db: Session = Depends(get_db)
):
    # TODO: For user-specific systems, ensure the client is authorized to index this note_id (e.g., based on note's owner_id).
    note_to_index: Optional[DBNoteForIndexSchema] = await get_note_by_id_for_indexing(db, request.note_id)
    if not note_to_index:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f"Note with ID {request.note_id} not found in database.")
    try:
        success, message, doc_id = index_service.add_note_to_index(note_to_index)
        response_status_str = "success" if success else "failed"
        http_status_code = status.HTTP_201_CREATED if success else status.HTTP_500_INTERNAL_SERVER_ERROR

        if not success:
            raise HTTPException(status_code=http_status_code, detail=message)

        return IndexOperationResponse(status=response_status_str, note_id=request.note_id, doc_id=doc_id,
                                      message=message)
    except HTTPException:
        raise  # Re-raise if it's already an HTTPException (like from the line above)
    except Exception as e:
        logger.exception(f"Error indexing note ID {request.note_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to index note by ID: {str(e)}")


@router.post(
    "/index/note/direct",
    response_model=IndexOperationResponse,
    summary="Index a Single Note with Provided Data",
    description="Adds/updates a note in the vector index using provided data (DocStore updated, new vectors added to FAISS).",
    status_code=status.HTTP_201_CREATED,
)
async def index_note_direct_endpoint(request: IndexSingleNoteRequest):
    # TODO: Ensure client is authorized to index this note (e.g., check request.note.owner_id against authenticated user).
    try:
        note_data_to_index: DBNoteForIndexSchema = request.note
        success, message, doc_id = index_service.add_note_to_index(note_data_to_index)
        response_status_str = "success" if success else "failed"
        http_status_code = status.HTTP_201_CREATED if success else status.HTTP_500_INTERNAL_SERVER_ERROR

        if not success:
            raise HTTPException(status_code=http_status_code, detail=message)

        return IndexOperationResponse(status=response_status_str, note_id=note_data_to_index.id, doc_id=doc_id,
                                      message=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error indexing note directly (ID: {request.note.id}): {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to index note directly: {str(e)}")


@router.delete(
    "/index/note/{note_id}",
    response_model=IndexOperationResponse,
    summary="Logically Delete a Note from Index",
    description="Logically removes a note by its ID from the index (removes from DocStore). Physical vector cleanup occurs during rebuilds.",
)
async def delete_note_from_index_endpoint(note_id: int):
    # TODO: Secure this. Ensure client is authorized to delete this specific note_id (e.g., check owner).
    try:
        success, message, doc_id = index_service.delete_note_from_index(note_id, persist_changes=True)

        current_status_str = "logically_deleted"
        http_status_code = status.HTTP_200_OK

        if not success:  # This means a more fundamental error in the service call itself
            current_status_str = "failed"
            http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif "not found" in message.lower():  # Service indicated it wasn't there
            current_status_str = "not_found"
            # http_status_code = status.HTTP_404_NOT_FOUND # Or keep 200 with status "not_found"

        if http_status_code >= 400:  # If it's an error status
            raise HTTPException(status_code=http_status_code, detail=message)

        return IndexOperationResponse(status=current_status_str, note_id=note_id, doc_id=doc_id, message=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error logically deleting note ID {note_id} from index: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to logically delete note: {str(e)}")


@router.get(
    "/index/stats",
    response_model=IndexStatsResponse,
    summary="Get Index Statistics",
    description="Retrieves statistics about the current vector index (FAISS vector count, DocStore doc count, FAISS type).",
)
async def get_index_stats_endpoint():
    try:
        count, message = index_service.get_index_statistics()
        if "Error" in message or "not available" in message or "not fully initialized" in message:  # Check if service indicated an error state
            raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=message)
        return IndexStatsResponse(total_indexed_vectors=count, message=message)
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Error getting index statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to retrieve index statistics: {str(e)}")


async def _background_rebuild_task(db_session_factory, force_rebuild_flag: bool,
                                   user_id_to_rebuild: Optional[int] = None):
    """Helper for running rebuild tasks in the background."""
    db_bg = db_session_factory()
    try:
        if user_id_to_rebuild is not None:
            logger.info(f"Background task started: Rebuilding index for user_id {user_id_to_rebuild}.")
            notes_processed, vectors_added, msg = await index_service.rebuild_index_for_user(db_bg, user_id_to_rebuild)
            logger.info(
                f"Background task finished for user_id {user_id_to_rebuild}: {msg}. Processed: {notes_processed}, New Nodes: {vectors_added}")
        else:  # Full rebuild
            logger.info(f"Background task started: Full index rebuild (force_rebuild={force_rebuild_flag}).")
            notes_processed, vectors_added = await index_service.build_full_index(db_bg,
                                                                                  force_rebuild=force_rebuild_flag)
            logger.info(
                f"Background task finished for full rebuild. Processed: {notes_processed}, Total Vectors: {vectors_added}")
    except Exception as e_bg:
        if user_id_to_rebuild is not None:
            logger.exception(f"Background task failed: Rebuilding index for user_id {user_id_to_rebuild}: {e_bg}")
        else:
            logger.exception(f"Background full rebuild task failed: {e_bg}")
    finally:
        db_bg.close()


@router.post(
    "/index/rebuild",
    response_model=RebuildStatusResponse,
    summary="Trigger Full Index Rebuild (All Users)",
    description="Triggers a full rebuild of the vector index from all notes in the database. Accepted for background processing.",
    status_code=status.HTTP_202_ACCEPTED
)
async def rebuild_full_index_endpoint(background_tasks: BackgroundTasks, db: Session = Depends(
    get_db)):  # db just to show it can be passed if needed by service
    # TODO: Secure this. This is a system-wide admin operation.
    logger.info("Full index rebuild endpoint triggered. Task (force_rebuild=True) will run in background.")
    background_tasks.add_task(_background_rebuild_task, AppSessionLocal, force_rebuild_flag=True,
                              user_id_to_rebuild=None)
    return RebuildStatusResponse(status="accepted",
                                 message="Full index rebuild process accepted (force_rebuild=True) and initiated in background.")


@router.delete(
    "/index/user/{user_id_in_path}/notes",
    response_model=UserNotesIndexOperationResponse,
    summary="Logically Delete All Indexed Notes for a User",
    description="Logically removes all notes for a specified user from the index (removes from DocStore). Physical cleanup during rebuilds.",
)
async def delete_user_notes_from_index_endpoint(
        user_id_in_path: int,
        db: Session = Depends(get_db)  # db session to fetch user's notes
):
    # TODO: Secure this. Ensure client is authorized to delete notes for user_id_in_path.
    logger.info(f"Endpoint triggered: Logically delete all notes for user_id {user_id_in_path} from index.")
    try:
        success, message, count_targeted = await index_service.delete_notes_by_user_from_index(db, user_id_in_path,
                                                                                               persist_changes=True)

        response_status_str = "logically_deleted_some_or_all"
        http_status_code = status.HTTP_200_OK

        if not success:  # Should indicate a more fundamental failure
            response_status_str = "failed_to_process_fully"
            http_status_code = status.HTTP_500_INTERNAL_SERVER_ERROR
        elif count_targeted == 0 and "No notes found" in message:  # Handled by service, but good to have distinct status
            response_status_str = "no_notes_found_for_user_in_db"

        if http_status_code >= 400:
            raise HTTPException(status_code=http_status_code, detail=message)

        return UserNotesIndexOperationResponse(
            status=response_status_str,
            user_id=user_id_in_path,
            notes_targeted_count=count_targeted,
            message=message
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error logically deleting notes for user {user_id_in_path} from index: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                            detail=f"Failed to logically delete user notes: {str(e)}")


@router.post(
    "/index/user/{user_id_in_path}/rebuild",
    response_model=RebuildStatusResponse,
    summary="Rebuild Index for a Specific User's Notes",
    description="Logically clears and re-indexes all notes for the specified user. Accepted for background processing.",
    status_code=status.HTTP_202_ACCEPTED
)
async def rebuild_user_index_endpoint(
        user_id_in_path: int,
        background_tasks: BackgroundTasks,
        # db: Session = Depends(get_db) # Not strictly needed here if background task gets its own session
):
    # TODO: Secure this. Ensure client is authorized to rebuild index for user_id_in_path.
    logger.info(f"Endpoint triggered: Rebuild index for user_id {user_id_in_path}. Task will run in background.")
    background_tasks.add_task(_background_rebuild_task, AppSessionLocal, force_rebuild_flag=False,
                              user_id_to_rebuild=user_id_in_path)
    return RebuildStatusResponse(
        status="accepted",
        user_id=user_id_in_path,
        message=f"Index rebuild process for user_id {user_id_in_path} has been accepted and initiated in the background."
    )