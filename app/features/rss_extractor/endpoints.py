# app/features/rss_extractor/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status

from .schemas import RssFeedRequest, RssFeedResponse
from . import service as rss_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=RssFeedResponse,
    summary="Extract Entries from an RSS Feed",
    description="Parses an RSS or Atom feed and returns a list of its entries, including their titles, links, and summaries.",
    tags=["V1 - RSS Extractor"]
)
async def extract_from_rss_feed(request: RssFeedRequest):
    try:
        feed_title, entries, error = await rss_service.extract_urls_from_feed(str(request.url))

        if error:
            # If the service identifies a parsing error, it's a client-side data issue
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail=error
            )

        return RssFeedResponse(
            feed_url=request.url,
            feed_title=feed_title,
            entries=entries
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /rss endpoint for URL '{request.url}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected server error occurred: {str(e)}"
        )