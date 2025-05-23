# app/features/web_crawl/crawler_service.py
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
from playwright.async_api import Error as PlaywrightError

# Feature-specific schemas and settings.
from app.features.web_crawl.schemas import SingleUrlCrawlResponse
from app.features.web_crawl.config import web_crawl_settings

logger = logging.getLogger(__name__)

async def _generate_simple_title(url: str, content: Optional[str]) -> str:
    if content:
        first_line = content.split('\n', 1)[0].strip()
        if first_line.startswith("# "): return first_line[2:].strip()
        if 5 < len(first_line) < 100: return first_line
    try:
        parsed_url = urlparse(url)
        path_name = Path(parsed_url.path).name
        if path_name and path_name != '/': return path_name.replace('-', ' ').replace('_', ' ').capitalize()
        return parsed_url.netloc
    except Exception: return "Crawled Content"

async def _crawl_url_with_instance(
    crawler_instance: AsyncWebCrawler, url: str, use_simplified_config: bool = False
) -> Tuple[Optional[str], Optional[str]]: # Returns (content_markdown, error_message)
    logger.info(f"Crawling: {url}")
    try:
        if use_simplified_config:
            run_config = CrawlerRunConfig(cache_mode=CacheMode.BYPASS, verbose=False)
        else:
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
            output_content = None
            if result.markdown:
                if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown and result.markdown.fit_markdown.strip():
                    output_content = result.markdown.fit_markdown.strip()
                elif hasattr(result.markdown, 'raw_markdown') and result.markdown.raw_markdown and result.markdown.raw_markdown.strip():
                    output_content = result.markdown.raw_markdown.strip()
                elif isinstance(result.markdown, str) and result.markdown.strip():
                    output_content = result.markdown.strip()

            if output_content:
                if len(output_content) > web_crawl_settings.MAX_CRAWL_CONTENT_LENGTH:
                    logger.warning(f"Content from {url} ({len(output_content)} chars) exceeded max length ({web_crawl_settings.MAX_CRAWL_CONTENT_LENGTH}), truncating.")
                    output_content = output_content[:web_crawl_settings.MAX_CRAWL_CONTENT_LENGTH]
                logger.info(f"Extracted ~{len(output_content.split())} words from: {url}")
                return output_content, None
            else:
                msg = f"Markdown generation for {url} produced no usable content."
                logger.warning(msg); return None, msg
        else:
            error_msg_detail = result.error_message if result else "Crawler returned None/non-success"
            status_code = result.status_code if result else "N/A"
            msg = f"Crawl failed for '{url}'. Status: {status_code}, Error: {error_msg_detail}"
            logger.error(msg); return None, msg
    except PlaywrightError as pe: msg = f"PlaywrightError ({type(pe).__name__}) crawling {url}: {str(pe)}"; logger.error(msg); return None, msg
    except asyncio.TimeoutError: msg = f"Crawl for {url} timed out."; logger.error(msg); return None, msg
    except Exception as e: msg = f"Unhandled exception crawling '{url}': {type(e).__name__} - {str(e)}"; logger.exception(msg); return None, msg

async def crawl_single_url(url_to_crawl: str) -> SingleUrlCrawlResponse:
    browser_cfg = BrowserConfig(headless=True, verbose=False)
    content_markdown: Optional[str] = None
    error_message: Optional[str] = None
    title: Optional[str] = None
    crawler: Optional[AsyncWebCrawler] = None

    try:
        crawler = AsyncWebCrawler(config=browser_cfg)
        await crawler.start()

        async with asyncio.timeout(web_crawl_settings.CRAWL_TIMEOUT_SECONDS):
            content_markdown, error_message = await _crawl_url_with_instance(
                crawler_instance=crawler, url=url_to_crawl
            )
    except asyncio.TimeoutError:
        error_message = f"Crawl for {url_to_crawl} timed out operationally after {web_crawl_settings.CRAWL_TIMEOUT_SECONDS}s."
        logger.error(error_message)
    except PlaywrightError as pe_manage:
        error_message = f"PlaywrightError managing crawler for {url_to_crawl}: {type(pe_manage).__name__} - {str(pe_manage)}"
        logger.error(error_message, exc_info=True)
    except Exception as e_manage:
        error_message = f"Unexpected error managing crawler for {url_to_crawl}: {type(e_manage).__name__} - {str(e_manage)}"
        logger.error(error_message, exc_info=True)
    finally:
        if crawler:
            try:
                await crawler.stop()
            except Exception as e_stop:
                logger.error(f"Error stopping crawler for {url_to_crawl}: {type(e_stop).__name__} - {str(e_stop)}", exc_info=True)
                if not error_message:
                    error_message = f"Error during crawler shutdown: {str(e_stop)}"

    status = "success" if content_markdown and not error_message else "failed"
    if status == "success" and content_markdown: # Ensure content_markdown is not None for title generation
        title = await _generate_simple_title(url_to_crawl, content_markdown)
    elif not error_message:
        error_message = "Crawling completed but no content was extracted or an unknown error occurred."

    return SingleUrlCrawlResponse(
        url=url_to_crawl, # type: ignore # Pydantic will validate HttpUrl
        status=status,
        content_markdown=content_markdown,
        title=title,
        error_message=error_message
    )

async def crawl_multiple_urls(urls_to_crawl: List[str]) -> List[SingleUrlCrawlResponse]:
    if not urls_to_crawl: return []
    tasks = [crawl_single_url(url) for url in urls_to_crawl]
    results_or_exceptions = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results: List[SingleUrlCrawlResponse] = []
    for i, res_or_exc in enumerate(results_or_exceptions):
        url_str = urls_to_crawl[i] # url is a string here
        if isinstance(res_or_exc, Exception):
            logger.error(f"Exception from gather for URL {url_str}: {res_or_exc}")
            processed_results.append(SingleUrlCrawlResponse(url=url_str, status="failed", error_message=f"Task failed: {type(res_or_exc).__name__}")) # type: ignore
        elif isinstance(res_or_exc, SingleUrlCrawlResponse):
            processed_results.append(res_or_exc)
        else:
             logger.error(f"Unexpected result type from gather for {url_str}: {type(res_or_exc)}")
             processed_results.append(SingleUrlCrawlResponse(url=url_str, status="failed", error_message="Unknown processing error.")) # type: ignore
    return processed_results