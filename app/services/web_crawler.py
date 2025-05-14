# app/services/web_crawler.py
import asyncio
import logging
from typing import Optional
from crawl4ai import AsyncWebCrawler
from crawl4ai.async_configs import BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.markdown_generation_strategy import DefaultMarkdownGenerator
from crawl4ai.content_filter_strategy import PruningContentFilter

logger = logging.getLogger(__name__)

async def crawl_and_extract_with_instance(
        crawler_instance: AsyncWebCrawler,
        url: str,
        use_simplified_config: bool = False
) -> Optional[str]:
    """
    Crawls a URL using a provided AsyncWebCrawler instance.
    """
    if not crawler_instance:
        logger.error("Crawler instance not provided to crawl_and_extract_with_instance for URL: %s", url)
        return None

    logger.info("Attempting to crawl (with instance) and extract content from: %s", url)
    try:
        if use_simplified_config:
            logger.info("USING SIMPLIFIED CrawlerRunConfig for URL: %s", url)
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, # Or CacheMode.NORMAL for caching
                verbose=True # Keep true if simplifying, for debug
            )
        else:
            logger.debug("Using standard CrawlerRunConfig for URL: %s", url)
            pruning_filter = PruningContentFilter(threshold=0.45, threshold_type="dynamic", min_word_threshold=10)
            md_generator = DefaultMarkdownGenerator(content_filter=pruning_filter)
            run_config = CrawlerRunConfig(
                cache_mode=CacheMode.BYPASS, # Or CacheMode.NORMAL for caching
                css_selector="article, .article-content, .post-content, main, #main, #content, body",
                excluded_tags=["nav", "footer", "header", "aside", "script", "style", "figure", "figcaption", "form"],
                word_count_threshold=20,
                markdown_generator=md_generator,
                verbose=False # Set to False for cleaner production logs from C4AI
            )

        result = await crawler_instance.arun(url=url, config=run_config)

        if result and result.success:
            output_content = None
            if result.markdown:
                # Prefer fit_markdown if available and has content
                if hasattr(result.markdown, 'fit_markdown') and result.markdown.fit_markdown and result.markdown.fit_markdown.strip():
                    output_content = result.markdown.fit_markdown.strip()
                    logger.debug("Using 'fit_markdown' (filtered content) from: %s", url)
                elif hasattr(result.markdown, 'raw_markdown') and result.markdown.raw_markdown and result.markdown.raw_markdown.strip():
                    output_content = result.markdown.raw_markdown.strip()
                    logger.debug("Using 'raw_markdown' (filter might have been bypassed or returned empty) from: %s", url)
                elif isinstance(result.markdown, str) and result.markdown.strip(): # Fallback for direct string
                    output_content = result.markdown.strip()
                    logger.debug("Using direct string from result.markdown for: %s", url)

            if output_content:
                logger.info("Successfully extracted (with instance) ~%d words from: %s", len(output_content.split()), url)
                return output_content
            else:
                logger.warning("Markdown generation (with instance) completed but produced no usable content for %s. Review selectors or content filters.", url)
                return None # Explicitly return None if no content
        else:
            error_msg = result.error_message if result else "Crawler returned None or result.success is False"
            status_code = result.status_code if result else "N/A"
            logger.error("Crawl (with instance) failed for URL '%s'. Status: %s, Error: %s", url, status_code, error_msg)
            return None
    except Exception as e:
        logger.exception("ERROR: Unhandled exception during crawl_and_extract_with_instance for URL '%s'", url)
        return None


# --- Standalone testing part (keeps its own crawler management) ---
async def _test_crawl_specific(url_to_test: str, simplified_run_config: bool = False):
    logger.info("\n--- Standalone Test: Testing crawl_and_extract_with_instance for: %s ---", url_to_test)
    logger.info("--- Standalone Test: Using simplified run config: %s ---", simplified_run_config)

    # For standalone test, create and manage crawler instance locally
    # Default to headless=True, verbose=False for closer parity with service usage
    browser_cfg_test = BrowserConfig(headless=True, verbose=False) # Can set verbose=True for C4AI logs
    content = None
    async with AsyncWebCrawler(config=browser_cfg_test) as standalone_crawler:
        logger.info("Standalone test crawler initialized.")
        content = await crawl_and_extract_with_instance(
            crawler_instance=standalone_crawler,
            url=url_to_test,
            use_simplified_config=simplified_run_config
        )
        logger.info("Standalone test crawler closed.")

    if content:
        logger.info("\n--- Standalone Test: Extracted Content (First 1000 chars) ---")
        print(content[:1000] + "...")
        logger.info("\n--- Standalone Test: Total extracted length: %d chars ---", len(content))
    else:
        logger.error("\n--- Standalone Test: Failed to extract content from %s ---", url_to_test)


if __name__ == "__main__":
    # Ensure logging is configured if running standalone
    if not logging.getLogger().hasHandlers():
        # Set to DEBUG for detailed logs during standalone testing
        logging.basicConfig(
            level=logging.DEBUG,
            format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            handlers=[logging.StreamHandler()]
        )

    # URL to test
    # specific_url_to_test = "https://my.clevelandclinic.org/health/diseases/15050-vitamin-d-vitamin-d-deficiency"
    specific_url_to_test = "https://ods.od.nih.gov/factsheets/VitaminD-HealthProfessional/" # Another test URL

    # --- Choose which config to test standalone ---
    test_with_simplified_config = False # Set to True to test with simplified run_config
    # test_with_simplified_config = True
    # --- ---

    # Standard asyncio run for scripts
    try:
        asyncio.run(_test_crawl_specific(specific_url_to_test, simplified_run_config=test_with_simplified_config))
    except RuntimeError as e:
        # Handle common asyncio loop issues if running in an environment like Jupyter
        if "cannot run loop" in str(e).lower() or "event loop is already running" in str(e).lower():
            logger.warning("Could not run test directly (loop might be running, e.g. in Jupyter).")
        elif "There is no current event loop in thread" in str(e): # Should be less common with asyncio.run
            logger.info("Manually creating and running event loop for standalone test.")
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(_test_crawl_specific(specific_url_to_test, simplified_run_config=test_with_simplified_config))
            finally:
                loop.close()
                asyncio.set_event_loop(None)
        else:
            logger.exception("Runtime error during standalone test execution.")
            # raise e # Optionally re-raise
    except Exception as e:
        logger.exception("General error during standalone test execution.")