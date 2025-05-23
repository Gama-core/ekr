# app/features/web_crawl/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status
from typing import List

# Import schemas and service specific to this web_crawl feature.
from app.features.web_crawl.schemas import (
    SingleUrlCrawlRequest, SingleUrlCrawlResponse,
    MultipleUrlsCrawlRequest
)
from app.features.web_crawl import crawler_service # Corrected import

logger = logging.getLogger(__name__)
router = APIRouter() # Router for Web Crawl feature endpoints.

# --- Web Crawling Service Endpoints ---
@router.post(
    "/single-url", # Endpoint will be /api/v1/crawl/single-url
    response_model=SingleUrlCrawlResponse,
    summary="Crawl a Single URL",
    description="Crawls a single URL and returns extracted content.",
    tags=["V1 - Web Crawl"] # Feature-specific tag
)
async def crawl_single_url_endpoint_impl(request: SingleUrlCrawlRequest): # Renamed function
    try:
        response = await crawler_service.crawl_single_url(str(request.url))
        if response.status == "failed" and "timeout" in (response.error_message or "").lower():
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=response.error_message)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /crawl/single-url for URL '{request.url}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during single URL crawl: {str(e)}"
        )

@router.post(
    "/multiple-urls", # Endpoint will be /api/v1/crawl/multiple-urls
    response_model=List[SingleUrlCrawlResponse],
    summary="Crawl Multiple URLs",
    description="Crawls a list of URLs concurrently.",
    tags=["V1 - Web Crawl"] # Feature-specific tag
)
async def crawl_multiple_urls_endpoint_impl(request: MultipleUrlsCrawlRequest): # Renamed function
    try:
        url_strings = [str(url) for url in request.urls]
        responses = await crawler_service.crawl_multiple_urls(url_strings)
        return responses
    except Exception as e:
        logger.exception(f"Unexpected error in /crawl/multiple-urls: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during multiple URL crawl: {str(e)}"
        )