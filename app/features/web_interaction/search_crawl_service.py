# app/features/web_interaction/search_crawl_service.py
import asyncio
import logging
from typing import List, Tuple  # Added Tuple

# Import schemas and services for this feature.
from app.features.web_interaction.schemas import (
    SearchThenCrawlRequest,
    SearchThenCrawlResultItem,
    GoogleSearchResultItem,  # For type hint
    SingleUrlCrawlResponse  # For type hint
)
from app.features.web_interaction.google_search_service import perform_google_search
from app.features.web_interaction.web_crawler_service import crawl_single_url

logger = logging.getLogger(__name__)


# Orchestrates Google search followed by crawling top results.
async def perform_search_then_crawl(
        request: SearchThenCrawlRequest
) -> List[SearchThenCrawlResultItem]:
    logger.info(
        f"Starting search-then-crawl: query='{request.query}', num_to_crawl={request.num_search_results_to_crawl}")

    search_results, search_error = await perform_google_search(
        query=request.query,
        num_results=request.num_search_results_to_crawl
    )

    if search_error:
        logger.error(f"Search failed for query '{request.query}': {search_error}")
        return [SearchThenCrawlResultItem(status="failed", error_message=f"Google Search failed: {search_error}")]
    if not search_results:
        logger.warning(f"No search results for query: '{request.query}'")
        return []

    # Prepare list of (URL string, search item, rank) for crawling.
    urls_to_crawl_with_meta: List[Tuple[str, GoogleSearchResultItem, int]] = []
    for i, sr_item in enumerate(search_results):
        if i >= request.num_search_results_to_crawl: break  # Limit to requested number.
        if sr_item.link:
            urls_to_crawl_with_meta.append((str(sr_item.link), sr_item, i + 1))
        else:
            logger.warning(f"Search result {i + 1} (title: {sr_item.title}) has no link for query '{request.query}'.")

    # Concurrently crawl the selected URLs.
    crawl_tasks = [crawl_single_url(url_str) for url_str, _, _ in urls_to_crawl_with_meta]
    crawl_responses_or_exceptions = await asyncio.gather(*crawl_tasks, return_exceptions=True)

    # app/features/web_interaction/search_crawl_service.py

    # ... (other code remains the same) ...

    final_results: List[SearchThenCrawlResultItem] = []
    for i, resp_or_exc in enumerate(crawl_responses_or_exceptions):
        original_url_str, original_sr_item, original_rank = urls_to_crawl_with_meta[i]

        # Base arguments, EXCLUDING 'url' because it will be taken from crawl_response
        base_item_args = {
            "original_search_rank": original_rank,
            "search_result_title": original_sr_item.title,
            "search_result_snippet": original_sr_item.snippet,
        }

        if isinstance(resp_or_exc, Exception):
            logger.error(f"Exception during crawl_single_url({original_url_str}): {resp_or_exc}")
            final_results.append(SearchThenCrawlResultItem(
                **base_item_args,  # Use base_item_args
                url=original_url_str,  # For failed crawls, use the original URL we attempted
                status="failed",
                error_message=f"Core crawling task failed: {type(resp_or_exc).__name__} - {str(resp_or_exc)}"
            ))
        elif isinstance(resp_or_exc, SingleUrlCrawlResponse):
            final_results.append(SearchThenCrawlResultItem(
                **base_item_args,  # Use base_item_args
                url=resp_or_exc.url,  # <<< Use the URL from the crawl response
                status=resp_or_exc.status,
                content_markdown=resp_or_exc.content_markdown,
                title=resp_or_exc.title,
                error_message=resp_or_exc.error_message
            ))
        else:  # Should not happen.
            logger.error(f"Unexpected result type from crawl of {original_url_str}: {type(resp_or_exc)}")
            final_results.append(SearchThenCrawlResultItem(
                **base_item_args,  # Use base_item_args
                url=original_url_str,  # Use original URL for unknown errors
                status="failed",
                error_message="Unknown error during crawl result processing."
            ))

    logger.info(f"Search-then-crawl completed for '{request.query}'. Processed {len(final_results)} items.")
    return final_results