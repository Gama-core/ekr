import logging
from fastapi import APIRouter, HTTPException, status

from .schemas import SummaryRequest, SummaryResponse
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/summarize", response_model=SummaryResponse, summary="Generate a Summary for a Note")
async def summarize_note_endpoint(request: SummaryRequest):
    """
    Generates a summary for the provided note data.
    - **summary_level**: Controls the length ('short', 'medium', 'detailed').
    - **summary_strategy**: Defines the method. Currently, only `root_only` is supported, which ignores any sub-notes.
    """
    try:
        response = await service.generate_summary(request)
        if response.error_message:
            # Error came from a downstream service (LLM Query)
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=response.error_message
            )
        return response
    except Exception as e:
        logger.exception(f"Unexpected error in /summarize endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {e}"
        )