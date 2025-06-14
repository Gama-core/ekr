import logging
from fastapi import APIRouter, HTTPException, status

from .schemas import RssFeedRequest, RssFeedResponse
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/extract", response_model=RssFeedResponse, summary="Extract Entries from an RSS Feed")
async def extract_from_rss_feed_endpoint(request: RssFeedRequest):
    """Parses an RSS or Atom feed and returns a list of its entries."""
    try:
        feed_title, entries, error = await service.extract_feed_entries(str(request.url))

        if error:
            # Determine appropriate status code based on the error
            if "Timeout" in error:
                status_code = status.HTTP_408_REQUEST_TIMEOUT
            elif "not well-formed" in error:
                status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            raise HTTPException(status_code=status_code, detail=error)

        return RssFeedResponse(
            feed_url=request.url,
            feed_title=feed_title,
            entries=entries
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /extract endpoint for URL '{request.url}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected server error occurred during RSS extraction."
        )