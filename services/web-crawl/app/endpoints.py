# app/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status
from typing import List

from .schemas import (SingleUrlCrawlRequest, SingleUrlCrawlResponse,
                      MultipleUrlsCrawlRequest)
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/single-url", response_model=SingleUrlCrawlResponse, summary="Crawl a Single URL")
async def crawl_single_url_endpoint(request: SingleUrlCrawlRequest):
    """Crawls a single URL and returns extracted content as Markdown."""
    try:
        response = await service.crawl_single_url(str(request.url))
        if response.status == "failed":
            if "timeout" in (response.error_message or "").lower():
                raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=response.error_message)
            # Use 502 for upstream failures (the crawl itself failed)
            raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=response.error_message)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /single-url for URL '{request.url}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred."
        )

@router.post("/multiple-urls", response_model=List[SingleUrlCrawlResponse], summary="Crawl Multiple URLs")
async def crawl_multiple_urls_endpoint(request: MultipleUrlsCrawlRequest):
    """Crawls a list of URLs concurrently and returns their results."""
    try:
        url_strings = [str(url) for url in request.urls]
        return await service.crawl_multiple_urls(url_strings)
    except Exception as e:
        logger.exception(f"Unexpected error in /multiple-urls: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected internal server error occurred."
        )