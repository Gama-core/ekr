import logging
from fastapi import APIRouter, HTTPException, status

from .schemas import GoogleSearchRequest, GoogleSearchResponse
from . import service
from .config import settings

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/search", response_model=GoogleSearchResponse, summary="Perform Google Search")
async def google_search_endpoint(request: GoogleSearchRequest):
    """Performs a Google search and returns structured results."""

    # Use the number of results from the request, falling back to the service default
    num_to_request = request.num_results or settings.DEFAULT_NUM_GOOGLE_RESULTS

    try:
        results, error = await service.perform_google_search(
            query=request.query,
            num_results=num_to_request
        )

        if error:
            # If the service layer caught an error, bubble it up with a 502 status
            raise HTTPException(
                status_code=status.HTTP_502_BAD_GATEWAY,
                detail=error
            )

        return GoogleSearchResponse(query_echo=request.query, results=results)

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /search endpoint for query '{request.query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during the search operation."
        )