import logging
from fastapi import APIRouter, HTTPException, status, BackgroundTasks
from . import index_service, retrieval_service, schemas
from .clients import database_client

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/retrieve", response_model=schemas.RetrieveResponse, summary="Retrieve Relevant Context (RAG)")
async def retrieve_context_endpoint(request: schemas.RetrieveRequest):
    try:
        items, message = await retrieval_service.retrieve_relevant_context(
            query_text=request.query, user_id=request.user_id, top_k_override=request.top_k
        )
        return schemas.RetrieveResponse(
            query_echo=request.query, user_id_echo=request.user_id, retrieved_items=items, message=message
        )
    except Exception as e:
        logger.exception(f"Error in /retrieve endpoint for user {request.user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))


@router.post("/index/note", response_model=schemas.IndexOperationResponse, summary="Index a Single Note by ID")
async def index_note_by_id_endpoint(request: schemas.IndexNoteByIdRequest):
    logger.info(f"API: Request to index note_id: {request.note_id}")
    note_to_index = await database_client.get_note_by_id(request.note_id)

    if not note_to_index:
        logger.warning(f"Note {request.note_id} not in DB. Triggering deletion from index.")
        success, msg, doc_id = index_service.delete_note_from_index(request.note_id)
        return schemas.IndexOperationResponse(status="deleted_from_index", note_id=request.note_id, doc_id=doc_id,
                                              message=msg)

    if not note_to_index.text_content or not note_to_index.text_content.strip():
        logger.warning(f"Note {request.note_id} has no content. Triggering deletion from index.")
        success, msg, doc_id = index_service.delete_note_from_index(request.note_id)
        return schemas.IndexOperationResponse(status="deleted_as_empty", note_id=request.note_id, doc_id=doc_id,
                                              message=msg)

    success, msg, doc_id = index_service.add_or_update_note_in_index(note_to_index)
    if not success:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=msg)

    return schemas.IndexOperationResponse(status="success", note_id=request.note_id, doc_id=doc_id, message=msg)


@router.delete("/index/note/{note_id}", response_model=schemas.IndexOperationResponse, summary="Delete Note from Index")
async def delete_note_from_index_endpoint(note_id: int):
    logger.info(f"API: Request to delete note_id: {note_id} from index.")
    success, msg, doc_id = index_service.delete_note_from_index(note_id)
    return schemas.IndexOperationResponse(status="delete_processed", note_id=note_id, doc_id=doc_id, message=msg)


@router.post("/index/rebuild", response_model=schemas.RebuildStatusResponse, summary="Trigger Full Index Rebuild")
async def rebuild_full_index_endpoint(background_tasks: BackgroundTasks):
    logger.info("API: Full index rebuild triggered. Task will run in background.")
    background_tasks.add_task(index_service.build_full_index, force_rebuild=True)
    return schemas.RebuildStatusResponse(status="accepted", message="Full index rebuild initiated in background.")


@router.get("/index/stats", response_model=schemas.IndexStatsResponse, summary="Get Detailed Index Statistics")
async def get_index_stats_endpoint():
    logger.info("Endpoint /index/stats called.")
    try:
        stats_dict = index_service.get_index_statistics()
        return schemas.IndexStatsResponse(**stats_dict)
    except Exception as e:
        logger.exception(f"Error getting statistics: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))