# app/features/llm_query/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status

# Import schemas and service specific to this llm_query feature.
from app.features.llm_query.schemas import LLMQueryRequest, LLMQueryResponse
from app.features.llm_query import llm_service

logger = logging.getLogger(__name__)
router = APIRouter() # Router for LLM Query feature endpoints.

@router.post(
    "/", # Endpoint will be /api/v1/llm/
    response_model=LLMQueryResponse,
    summary="Generic LLM Query",
    description="Sends a prompt to the configured LLM and returns the response.",
    tags=["V1 - LLM Query"] # Feature-specific tag
)
async def llm_query_endpoint(request: LLMQueryRequest):
    try:
        response_text, usage_info, error_message, model_used = await llm_service.generate_llm_response(
            user_prompt=request.user_prompt,
            system_prompt=request.system_prompt,
            model_name=request.model_name,
            max_tokens=request.max_tokens,
            temperature=request.temperature,
            additional_params=request.additional_params
        )

        if error_message:
            # Determine appropriate HTTP status code based on error
            # For now, using 502 for upstream LLM issues, 500 for others.
            # Client errors (4xx) would typically be caught before calling the service.
            http_status = status.HTTP_502_BAD_GATEWAY if "API Error" in error_message or "LLM client not initialized" in error_message else status.HTTP_500_INTERNAL_SERVER_ERROR
            # Log the error before raising HTTPException if it's a server-side issue
            if http_status >= 500:
                 logger.error(f"LLM service error for user_prompt '{request.user_prompt[:50]}...': {error_message}")

            raise HTTPException(
                status_code=http_status,
                detail=error_message
            )

        return LLMQueryResponse(
            response_text=response_text,
            model_used=model_used,
            usage_info=usage_info
        )
    except HTTPException:
        raise # Re-raise HTTPExceptions directly (e.g., from above)
    except Exception as e:
        # This catches truly unexpected errors in the endpoint logic itself.
        logger.exception(f"Unexpected error in /llm endpoint for user_prompt '{request.user_prompt[:50]}...': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing your LLM query: {str(e)}"
        )