import logging
from fastapi import APIRouter, HTTPException, status

from .schemas import FactCheckRequest, FactCheckResponse
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/fact-check", response_model=FactCheckResponse, summary="Fact-Check a Note")
async def fact_check_endpoint(request: FactCheckRequest):
    """
    Analyzes a note for factual inaccuracies and provides corrective suggestions.
    - **check_type**: Defines the method. Currently, only `corrective_suggestions` is supported.
    """
    try:
        response = await service.generate_fact_check(request)
        if response.error_message:
            # Errors from downstream (LLM service) or parsing errors
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=response.error_message
            )
        return response
    except Exception as e:
        logger.exception(f"Unexpected error in /fact-check endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {e}"
        )