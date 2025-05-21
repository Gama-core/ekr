# app/features/web_interaction/web_crawler_service.py
import asyncio
import logging
from typing import Optional, List, Tuple
from urllib.parse import urlparse
from pathlib import Path

# Third-party libraries for web crawling.
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from playwright.async_api import Error as PlaywrightError # Specific Playwright errors.

# Feature-specific schemas and settings.
from app.features.web_interaction.schemas import SingleUrlCrawlResponse
from app.features.web_interaction.config import web_interaction_settings

logger = logging.getLogger(__name__)

# Generates a simple fallback title from URL or content.
async def _generate_simple_title(url: str, content: Optional[str]) -> str:
    if content: # Try to extract from Markdown H1 or first reasonable line.
        first_line = content.split('\n', 1)[0].strip()
        if first_line.startswith("# "): return first_line[2:].strip()
        if 5 < len(first_line) < 100: return first_line
    try: # Fallback to URL parsing.
        parsed_url = urlparse(url)
        path_name = Path(parsed_url.path).name
        if path_name and path_name != '/': return path_name.replace('-', ' ').replace('_', ' ').capitalize()
        return parsed_url.netloc
    except Exception: return "Crawled Content" # Generic fallback.

# Internal helper to crawl a URL using a provided AsyncWebCrawler instance.
async def _crawl_url_with_instance(
    crawler_instance: AsyncWebCrawler, url: str, use_simplified_config: bool = False
) -> Tuple[Optional[str], Optional[str]]: # Returns (content_markdown, error_message)
    logger.info(f"Crawling: {url}")
    try:
        # Configure crawler run: simplified for basic fetch or detailed for content extraction.
        if use_simplified_config:
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        else: # Standard config with content filtering and specific selectors.
            pruning_filter = PruningContentFilter(threshold=0.45, threshold_type="dynamic", min_word_threshold=10)
            md_generator = DefaultMarkdownGenerator(content_filter=pruning_filter)
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS,
                css_selector="article, .article-content, .post-content, main, #main, #content, body",
                excluded_tags=["nav", "footer", "header", "aside", "script", "style", "figure", "figcaption", "form"],
                word_count_threshold=20, markdown_generator=md_generator, verbose=False
            )
        result = await crawler_instance.arun(url=url, config=run_config)

        if result and result.success:
            output_content = None # Determine best available Markdown content.
            if result.markdown:
                if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown and result.markdown.fit_markdown.strip():
                    output_content = result.markdown.fit_markdown.strip()
                elif hasattr(result.markdown, 'raw_markdown') and result.markdown.raw_markdown and result.markdown.raw_markdown.strip():
                    output_content = result.markdown.raw_markdown.strip()
                elif isinstance(result.markdown, str) and result.markdown.strip():
                    output_content = result.markdown.strip()

            if output_content: # Truncate if content exceeds max length.
                if len(output_content) > web_interaction_settings.MAX_CRAWL_CONTENT_LENGTH:
                    logger.warning(f"Content from {url} exceeded max length, truncating.")
                    output_content = output_content[:web_interaction_settings.MAX_CRAWL_CONTENT_LENGTH]
                logger.info(f"Extracted ~{len(output_content.split())} words from: {url}")
                return output_content, None
            else: # Crawl success but no usable content.
                msg = f"Markdown generation for {url} produced no usable content."
                logger.warning(msg); return None, msg
        else: # Crawl attempt failed.
            error_msg = result.error_message if result else "Crawler returned None/non-success"
            status_code = result.status_code if result else "N/A"
            msg = f"Crawl failed for '{url}'. Status: {status_code}, Error: {error_msg}"
            logger.error(msg); return None, msg
    # Catch specific and general exceptions during crawling.
    except PlaywrightError as pe: msg = f"PlaywrightError ({type(pe).__name__}) crawling {url}: {str(pe)}"; logger.error(msg); return None, msg
    except asyncio.TimeoutError: msg = f"Crawl for {url} timed out."; logger.error(msg); return None, msg
    except Exception as e: msg = f"Unhandled exception crawling '{url}': {type(e).__name__} - {str(e)}"; logger.exception(msg); return None, msg

# Crawls a single URL, managing its own crawler instance and timeout.
async def crawl_single_url(url_to_crawl: str) -> SingleUrlCrawlResponse:
    browser_cfg = BrowserConfig(headless=True, verbose=False)
    content_markdown: Optional[str] = None
    error_message: Optional[str] = None
    title: Optional[str] = None
    crawler: Optional[AsyncWebCrawler] = None # Keep a reference

    try:
        # Instantiate crawler outside the main timeout for its core operation
        crawler = AsyncWebCrawler(config=browser_cfg)
        await crawler.start() # Manually start the crawler (equivalent to __aenter__)

        # Timeout only for the crawl operation itself
        async with asyncio.timeout(web_interaction_settings.CRAWL_TIMEOUT_SECONDS):
            content_markdown, error_message = await _crawl_url_with_instance(
                crawler_instance=crawler, url=url_to_crawl
            )

    except asyncio.TimeoutError:
        error_message = f"Crawl for {url_to_crawl} timed out operationally after {web_interaction_settings.CRAWL_TIMEOUT_SECONDS}s."
        logger.error(error_message)
    except PlaywrightError as pe_manage: # Catch Playwright errors during start/stop
        error_message = f"PlaywrightError managing crawler for {url_to_crawl}: {type(pe_manage).__name__} - {str(pe_manage)}"
        logger.error(error_message, exc_info=True) # Log with traceback for these
    except Exception as e_manage: # Catch broader exceptions during crawler setup/teardown
        error_message = f"Unexpected error managing crawler for {url_to_crawl}: {type(e_manage).__name__} - {str(e_manage)}"
        logger.error(error_message, exc_info=True) # Log with traceback
    finally:
        if crawler:
            try:
                await crawler.stop() # Manually stop the crawler (equivalent to __aexit__)
            except Exception as e_stop:
                # Log error during stop but don't overwrite primary error_message if one already exists
                logger.error(f"Error stopping crawler for {url_to_crawl}: {type(e_stop).__name__} - {str(e_stop)}", exc_info=True)
                if not error_message: # Only set if no other error occurred
                    error_message = f"Error during crawler shutdown: {str(e_stop)}"


    status = "success" if content_markdown and not error_message else "failed"
    if status == "success":
        title = await _generate_simple_title(url_to_crawl, content_markdown)
    elif not error_message: # If status is failed but no specific error, provide one
        error_message = "Crawling completed but no content was extracted or an unknown error occurred."

    return SingleUrlCrawlResponse(
        url=url_to_crawl,
        status=status,
        content_markdown=content_markdown,
        title=title,
        error_message=error_message
    )
# Crawls multiple URLs concurrently.
async def crawl_multiple_urls(urls_to_crawl: List[str]) -> List[SingleUrlCrawlResponse]:
    if not urls_to_crawl: return []
    # Each crawl_single_url manages its own lifecycle; gather runs them concurrently.
    tasks = [crawl_single_url(url) for url in urls_to_crawl]
    results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results: List[SingleUrlCrawlResponse] = []
    for i, res_or_exc in enumerate(results_or_exceptions): # Process results, handling exceptions from gather.
        url = urls_to_crawl[i]
        if isinstance(res_or_exc, Exception):
            logger.error(f"Exception from gather for URL {url}: {res_or_exc}")
            processed_results.append(SingleUrlCrawlResponse(url=url, status="failed", error_message=f"Task failed: {type(res_or_exc).__name__}"))
        elif isinstance(res_or_exc, SingleUrlCrawlResponse):
            processed_results.append(res_or_exc)
        else: # Should not occur.
             logger.error(f"Unexpected result type from gather for {url}: {type(res_or_exc)}")
             processed_results.append(SingleUrlCrawlResponse(url=url, status="failed", error_message="Unknown processing error."))
    return processed_results