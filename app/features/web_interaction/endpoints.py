# app/features/web_interaction/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status
from typing import List

# Import schemas and services specific to this web_interaction feature.
from app.features.web_interaction.schemas import (
    GoogleSearchRequest, GoogleSearchResponse,
    SingleUrlCrawlRequest, SingleUrlCrawlResponse,
    MultipleUrlsCrawlRequest,
    SearchThenCrawlRequest, SearchThenCrawlResultItem
)
from app.features.web_interaction import google_search_service
from app.features.web_interaction import web_crawler_service
from app.features.web_interaction import search_crawl_service

logger = logging.getLogger(__name__)
router = APIRouter() # Router for web interaction feature endpoints.

# --- Feature 1: Google Search Service Endpoint ---
@router.post(
    "/search",
    response_model=GoogleSearchResponse,
    summary="Perform Google Search",
    description="Performs a Google search and returns structured results.",
    tags=["V1 - Web Interaction"] # Consolidated tag
)
async def google_search_endpoint(request: GoogleSearchRequest):
    try:
        results, error = await google_search_service.perform_google_search(
            query=request.query,
            num_results=request.num_results
        )
        # Return results with an error message if search failed, otherwise just results.
        return GoogleSearchResponse(query_echo=request.query, results=results, error_message=error)
    except Exception as e:
        logger.exception(f"Unexpected error in /search endpoint for query '{request.query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An unexpected error occurred during Google search."
        )

# --- Feature 2: Web Crawling Service Endpoints ---
@router.post(
    "/crawl/single-url",
    response_model=SingleUrlCrawlResponse,
    summary="Crawl a Single URL",
    description="Crawls a single URL and returns extracted content.",
    tags=["V1 - Web Interaction"]
)
async def crawl_single_url_endpoint(request: SingleUrlCrawlRequest):
    try:
        response = await web_crawler_service.crawl_single_url(str(request.url))
        # Handle specific timeout errors with appropriate HTTP status.
        if response.status == "failed" and "timeout" in (response.error_message or "").lower():
            raise HTTPException(status_code=status.HTTP_408_REQUEST_TIMEOUT, detail=response.error_message)
        return response
    except HTTPException:
        raise # Re-raise known HTTP exceptions.
    except Exception as e:
        logger.exception(f"Unexpected error in /crawl/single-url for URL '{request.url}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during single URL crawl: {str(e)}"
        )

@router.post(
    "/crawl/multiple-urls",
    response_model=List[SingleUrlCrawlResponse],
    summary="Crawl Multiple URLs",
    description="Crawls a list of URLs concurrently.",
    tags=["V1 - Web Interaction"]
)
async def crawl_multiple_urls_endpoint(request: MultipleUrlsCrawlRequest):
    try:
        url_strings = [str(url) for url in request.urls] # Convert HttpUrl to string for service.
        responses = await web_crawler_service.crawl_multiple_urls(url_strings)
        return responses
    except Exception as e:
        logger.exception(f"Unexpected error in /crawl/multiple-urls: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during multiple URL crawl: {str(e)}"
        )

# --- Feature 3: Search-Then-Crawl Orchestration Endpoint ---
@router.post(
    "/search-and-crawl-results",
    response_model=List[SearchThenCrawlResultItem],
    summary="Search and Crawl Top Results",
    description="Searches Google and crawls top results.",
    tags=["V1 - Web Interaction"]
)
async def search_and_crawl_results_endpoint(request: SearchThenCrawlRequest):
    try:
        results = await search_crawl_service.perform_search_then_crawl(request)
        return results
    except Exception as e:
        logger.exception(f"Unexpected error in /search-and-crawl-results for query '{request.query}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred during search-and-crawl: {str(e)}"
        )