# app/features/google_search/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status

# Import schemas and service specific to this google_search feature.
from app.features.google_search.schemas import (
    GoogleSearchRequest, GoogleSearchResponse
)
from app.features.google_search import search_service # Corrected import

logger = logging.getLogger(__name__)
router = APIRouter() # Router for Google Search feature endpoints.

# --- Google Search Service Endpoint ---
@router.post(
    "/", # Endpoint will be /api/v1/search/
    response_model=GoogleSearchResponse,
    summary="Perform Google Search",
    description="Performs a Google search and returns structured results.",
    tags=["V1 - Google Search"] # Feature-specific tag
)
async def google_search_endpoint_impl(request: GoogleSearchRequest): # Renamed function
    try:
        # Use the num_results from the request, or feature default if not provided (though schema has default)
        num_to_request = request.num_results

        results, error = await search_service.perform_google_search(
            query=request.query,
            num_results=num_to_request
        )
        return GoogleSearchResponse(query_echo=request.query, results=results, error_message=error)
    except Exception as e:
        logger.exception(f"Unexpected error in /search endpoint for query '{request.query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during Google search."
        )