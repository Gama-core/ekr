import logging
from fastapi import APIRouter, HTTPException, status, Body

from .schemas import UpdateRequest, UpdateResponse
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/update", response_model=UpdateResponse, summary="Update Note Content")
async def update_note_endpoint(request: UpdateRequest):
    """
    Updates the content of a note based on the chosen strategy:

    - **`autonomous`**: The service finds and fixes outdated info on its own.
    - **`guided`**: The service applies a specific list of corrections you provide.

    Both strategies return a unified response containing the full updated text and a detailed changelog.
    """
    try:
        response = await service.generate_update(request)
        if response.error_message:
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=response.error_message)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /update endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(e))