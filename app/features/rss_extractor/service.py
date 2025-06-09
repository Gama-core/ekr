# app/features/rss_extractor/service.py
import datetime
import logging
import asyncio
import feedparser
from typing import List, Optional, Tuple

from .schemas import RssEntryItem

logger = logging.getLogger(__name__)


async def extract_urls_from_feed(feed_url: str) -> Tuple[Optional[str], List[RssEntryItem], Optional[str]]:
    """
    Fetches and parses an RSS feed to extract entries.

    Returns:
        A tuple: (feed_title, list_of_entries, error_message)
    """
    logger.info(f"Attempting to parse RSS feed from URL: {feed_url}")
    try:
        # feedparser is a blocking library, so we run it in a thread pool executor
        def _blocking_parse():
            return feedparser.parse(feed_url)

        loop = asyncio.get_running_loop()
        parsed_feed = await loop.run_in_executor(None, _blocking_parse)

        if parsed_feed.bozo:
            bozo_exception = parsed_feed.get("bozo_exception")
            error_msg = f"Feed at {feed_url} is not well-formed or could not be parsed. Reason: {bozo_exception}"
            logger.warning(error_msg)
            # You can decide to return partial results or fail completely. Failing is safer.
            return None, [], error_msg

        feed_title = parsed_feed.feed.get("title")
        extracted_entries: List[RssEntryItem] = []

        for entry in parsed_feed.entries:
            # The 'published_parsed' attribute provides a structured time object
            pub_date = datetime.datetime(*entry.published_parsed[:6]) if hasattr(entry,
                                                                                 'published_parsed') and entry.published_parsed else None

            extracted_entries.append(
                RssEntryItem(
                    title=entry.get("title"),
                    link=entry.link,  # The .link attribute is almost always present
                    summary=entry.get("summary"),
                    published_date=pub_date,
                )
            )

        logger.info(f"Successfully extracted {len(extracted_entries)} entries from feed '{feed_title}'.")
        return feed_title, extracted_entries, None

    except Exception as e:
        error_msg = f"An unexpected error occurred while processing feed {feed_url}: {type(e).__name__} - {str(e)}"
        logger.exception(error_msg)
        return None, [], error_msg