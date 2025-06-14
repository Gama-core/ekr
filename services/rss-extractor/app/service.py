import datetime
import logging
import asyncio
import feedparser
import socket
from typing import List, Optional, Tuple

from .schemas import RssEntryItem
from .config import settings

logger = logging.getLogger(__name__)


async def extract_feed_entries(feed_url: str) -> Tuple[Optional[str], List[RssEntryItem], Optional[str]]:
    """
    Fetches and parses an RSS feed, returning entries or an error message.
    """
    logger.info(f"Attempting to parse RSS feed from URL: {feed_url}")

    try:
        # feedparser is a blocking library, so we run it in a thread pool.
        def _blocking_parse():
            # Set a socket timeout to prevent indefinite hangs
            socket.setdefaulttimeout(settings.FEED_FETCH_TIMEOUT_SECONDS)
            return feedparser.parse(feed_url)

        loop = asyncio.get_running_loop()
        parsed_feed = await loop.run_in_executor(None, _blocking_parse)

        # Reset socket timeout to default
        socket.setdefaulttimeout(None)

        if parsed_feed.bozo:
            # Bozo flag is set if the feed is not well-formed.
            bozo_exception = parsed_feed.get("bozo_exception", "Unknown parsing error")
            # Filter out common timeout exceptions which are not malformed feed errors
            if isinstance(bozo_exception, (socket.timeout, TimeoutError)):
                error_msg = f"Timeout error while fetching feed: {feed_url}"
            else:
                error_msg = f"Feed at {feed_url} is not well-formed. Reason: {bozo_exception}"
            logger.warning(error_msg)
            return None, [], error_msg

        feed_title = parsed_feed.feed.get("title")
        extracted_entries: List[RssEntryItem] = []

        for entry in parsed_feed.entries:
            # The 'published_parsed' attribute provides a structured time object
            pub_date = datetime.datetime(*entry.published_parsed[:6]) if hasattr(entry,
                                                                                 'published_parsed') and entry.published_parsed else None

            # Ensure the entry has a link, otherwise it's not useful
            if not hasattr(entry, 'link'):
                logger.warning(f"Skipping entry with title '{entry.get('title')}' because it has no link.")
                continue

            extracted_entries.append(
                RssEntryItem(
                    title=entry.get("title"),
                    link=entry.link,
                    summary=entry.get("summary"),
                    published_date=pub_date,
                )
            )

        logger.info(f"Successfully extracted {len(extracted_entries)} entries from feed '{feed_title}'.")
        return feed_title, extracted_entries, None

    except Exception as e:
        error_msg = f"An unexpected error occurred while processing feed {feed_url}: {type(e).__name__} - {e}"
        logger.exception(error_msg)
        return None, [], error_msg