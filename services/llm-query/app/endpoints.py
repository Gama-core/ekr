import logging
from fastapi import APIRouter, HTTPException, status

from .schemas import LLMQueryRequest, LLMQueryResponse
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/query", response_model=LLMQueryResponse, summary="Generic LLM Query")
async def llm_query_endpoint(request: LLMQueryRequest):
    """Sends a prompt to the configured LLM and returns the structured response."""
    try:
        response_text, usage_info, error_message, model_used = await service.generate_llm_response(request)

        if error_message:
            # Determine appropriate HTTP status code
            is_client_error = "LLM client not available" in error_message
            status_code = status.HTTP_503_SERVICE_UNAVAILABLE if is_client_error else status.HTTP_502_BAD_GATEWAY
            raise HTTPException(status_code=status_code, detail=error_message)

        return LLMQueryResponse(
            response_text=response_text,
            model_used=model_used,
            usage_info=usage_info
        )
    except HTTPException:
        raise # Re-raise exceptions that are already processed
    except Exception as e:
        logger.exception(f"Unexpected error in /query endpoint for prompt '{request.user_prompt[:50]}...': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected server error occurred: {e}")