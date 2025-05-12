# app/services/web_context_service.py
import logging
from typing import Optional, Tuple, List

from app import schemas
from app.services import google_search, llm_service, web_crawler
from app.core.config import settings # If needed for constants like MAX_URLS_TO_TRY

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig
from playwright.async_api import Error as PlaywrightError

logger = logging.getLogger(__name__)

# Constants (can be moved to config if needed)
SEARCH_QUERY_GENERATION_SYSTEM_PROMPT = """
You are an expert search query formulator. Based on the user's question, generate a concise and effective Google search query that will help find the most relevant web page to answer it. Return ONLY the search query, nothing else.
"""
MAX_CONTEXT_LENGTH = 3500 # Max characters to feed LLM
MAX_URLS_TO_TRY = 3      # Limit attempts for web context


async def generate_search_query(user_query: str) -> Optional[str]:
    """Generates a search query using an LLM."""
    logger.info(f"Generating search query for: '{user_query[:50]}...'")
    search_query_prompt = f"User's original question: \"{user_query}\""
    generated_search_query = await llm_service.generate_llm_response(
        system_prompt=SEARCH_QUERY_GENERATION_SYSTEM_PROMPT,
        user_prompt=search_query_prompt,
        max_tokens=60,
        temperature=0.2
    )
    if not generated_search_query or "Error" in generated_search_query:
        logger.error(f"LLM failed to generate search query. Response: {generated_search_query}")
        return None
    logger.info(f"Generated search query: '{generated_search_query}'")
    return generated_search_query.strip().strip('"') # Clean up quotes


async def search_and_crawl_for_context(
    search_query: str,
    max_urls: int = MAX_URLS_TO_TRY
) -> Tuple[Optional[str], Optional[schemas.assistant.Source]]:
    """
    Performs web search, crawls the first successful result, and extracts text.

    Returns:
        A tuple containing:
        - The extracted text content (str) or None if failed.
        - A Source schema object for the crawled URL or None if failed.
    """
    logger.info(f"Searching and crawling for context based on query: '{search_query}'")
    urls_found = await google_search.search_web(query=search_query, num_results=max_urls)

    if not urls_found:
        logger.warning(f"No URLs found for search query: '{search_query}'")
        return None, None

    crawled_text: Optional[str] = None
    crawled_source: Optional[schemas.assistant.Source] = None

    for i, target_url in enumerate(urls_found):
        if i >= max_urls: break # Safety break

        logger.info(f"Attempting crawl {i + 1}/{len(urls_found)}: {target_url}")
        try:
            browser_cfg = BrowserConfig(headless=True, verbose=False)
            async with AsyncWebCrawler(config=browser_cfg) as crawler:
                temp_crawled_text = await web_crawler.crawl_and_extract_with_instance(
                    crawler_instance=crawler, url=target_url
                )

            if temp_crawled_text:
                crawled_text = temp_crawled_text[:MAX_CONTEXT_LENGTH] # Truncate
                # Attempt to create a title (simple version)
                page_title = target_url.split('/')[-1] or target_url.split('/')[-2] or f"Content from {target_url}"
                crawled_source = schemas.assistant.Source(
                    type="web",
                    id=target_url, # Use URL as ID for web source
                    title=page_title, # Basic title extraction
                    url=target_url
                )
                logger.info(f"Successfully crawled and extracted from {target_url}")
                break # Exit loop on first success
            else:
                logger.warning(f"No usable content extracted from {target_url}")

        except PlaywrightError as pe:
            logger.error(f"PlaywrightError ({type(pe).__name__}) while crawling {target_url}: {str(pe)}")
        except Exception as e_crawl:
            logger.exception(f"Unexpected error ({type(e_crawl).__name__}) crawling {target_url}")

    if not crawled_text:
        logger.error(f"Failed to crawl or extract usable content from any of the {len(urls_found)} URLs.")
        return None, None

    return crawled_text, crawled_source

# You might add a higher-level function combining the two above
async def get_web_context_for_query(
    user_query: str
) -> Tuple[Optional[str], Optional[schemas.assistant.Source], Optional[List[str]]]:
    """
    Orchestrates getting web context: generate query -> search & crawl.

    Returns:
        A tuple containing:
        - Extracted text (str) or None
        - Source object or None
        - Intermediate steps/details (List[str]) or None (for potential logging/debugging)
    """
    intermediate_details = []
    generated_query = await generate_search_query(user_query)
    if not generated_query:
        intermediate_details.append("Failed to generate a search query via LLM.")
        return None, None, intermediate_details
    else:
        intermediate_details.append(f"Generated search query: '{generated_query}'")

    intermediate_details.append(f"Searching and attempting to crawl based on generated query.")
    text, source = await search_and_crawl_for_context(generated_query)

    if text and source:
        intermediate_details.append(f"Successfully retrieved context from: {source.url}")
    else:
        intermediate_details.append("Failed to retrieve usable context from the web after search and crawl attempts.")

    return text, source, intermediate_details