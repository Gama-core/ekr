# app/service.py
import asyncio
import logging
from typing import Optional, List, Tuple, Literal
from urllib.parse import urlparse
from pathlib import Path

from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter
from playwright.async_api import Error as PlaywrightError

from .schemas import SingleUrlCrawlResponse
from .config import settings

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
    except Exception:
        return "Crawled Content"


async def _crawl_url_with_instance(
        crawler_instance: AsyncWebCrawler, url: str
) -> Tuple[Optional[str], Optional[str]]:
    logger.info(f"Crawling: {url}")
    try:
        pruning_filter = PruningContentFilter(threshold=0.45, threshold_type="dynamic", min_word_threshold=10)
        md_generator = DefaultMarkdownGenerator(content_filter=pruning_filter)
        run_config = CrawlerRunConfig(
            cache_mode=CacheMode.BYPASS,
            css_selector="article, .article-content, .post-content, main, #main, #content, body",
            excluded_tags=["nav", "footer", "header", "aside", "script", "style", "figure", "figcaption", "form"],
            word_count_threshold=20, markdown_generator=md_generator, verbose=False
        )
        result = await crawler_instance.arun(url=url, config=run_config)

        if result and result.success and hasattr(result, 'markdown') and result.markdown:
            output_content = str(result.markdown).strip()
            if output_content:
                if len(output_content) > settings.MAX_CRAWL_CONTENT_LENGTH:
                    logger.warning(f"Content from {url} exceeded max length, truncating.")
                    output_content = output_content[:settings.MAX_CRAWL_CONTENT_LENGTH]
                logger.info(f"Extracted ~{len(output_content.split())} words from: {url}")
                return output_content, None

        error_detail = result.error_message if result and result.error_message else "Crawler returned non-success or empty content"
        status_code = result.status_code if result else 'N/A'
        msg = f"Crawl failed for '{url}'. Status: {status_code}, Error: {error_detail}"
        logger.error(msg)
        return None, msg

    except PlaywrightError as pe:
        msg = f"PlaywrightError crawling {url}: {pe}"
        logger.error(msg)
        return None, msg
    except asyncio.TimeoutError: # Catching timeout here is more specific
        msg = f"Crawl for {url} timed out within the crawler's 'arun' execution."
        logger.error(msg)
        return None, msg
    except Exception as e:
        msg = f"Unhandled exception crawling '{url}': {type(e).__name__} - {e}"
        logger.exception(msg)
        return None, msg


async def crawl_single_url(url_to_crawl: str) -> SingleUrlCrawlResponse:
    browser_cfg = BrowserConfig(headless=True, verbose=False)
    crawler: Optional[AsyncWebCrawler] = None
    content_markdown, error_message, title = None, None, None

    try:
        crawler = AsyncWebCrawler(config=browser_cfg)
        await crawler.start()

        async with asyncio.timeout(settings.CRAWL_TIMEOUT_SECONDS):
            content_markdown, error_message = await _crawl_url_with_instance(crawler, url_to_crawl)

    except asyncio.TimeoutError:
        error_message = f"Crawl operation for {url_to_crawl} timed out after {settings.CRAWL_TIMEOUT_SECONDS}s."
        logger.error(error_message)
    except Exception as e:
        error_message = f"Unexpected error managing crawler for {url_to_crawl}: {e}"
        logger.error(error_message, exc_info=True)
    finally:
        if crawler:
            try:
                await crawler.close()
            except Exception as e_stop:
                logger.error(f"Error stopping crawler for {url_to_crawl}: {e_stop}", exc_info=True)
                if not error_message:
                    error_message = f"Error during crawler shutdown: {str(e_stop)}"

    status: Literal["success", "failed"] = "success" if content_markdown and not error_message else "failed"
    if status == "success" and content_markdown:
        title = await _generate_simple_title(url_to_crawl, content_markdown)
    elif not error_message:
        error_message = "Crawling completed but no content was extracted."

    return SingleUrlCrawlResponse(
        url=url_to_crawl, # type: ignore
        status=status,
        content_markdown=content_markdown,
        title=title,
        error_message=error_message
    )

async def crawl_multiple_urls(urls_to_crawl: List[str]) -> List[SingleUrlCrawlResponse]:
    if not urls_to_crawl:
        return []
    tasks = [crawl_single_url(url) for url in urls_to_crawl]
    results = await asyncio.gather(*tasks, return_exceptions=True)

    processed_results: List[SingleUrlCrawlResponse] = []
    for i, res in enumerate(results):
        url = urls_to_crawl[i]
        if isinstance(res, Exception):
            logger.error(f"Exception from gather for URL {url}: {res}", exc_info=True)
            processed_results.append(SingleUrlCrawlResponse(url=url, status="failed", error_message=f"Task failed: {type(res).__name__}")) # type: ignore
        elif isinstance(res, SingleUrlCrawlResponse):
            processed_results.append(res)
    return processed_results