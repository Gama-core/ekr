# app/services/google_search.py

import asyncio
import logging # Import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings

logger = logging.getLogger(__name__) # Create a logger instance

async def search_web(query: str, num_results: int = 5) -> list[str]: # Default to 5
    """
    Performs a web search using the Google Custom Search JSON API.

    Args:
        query: The search term.
        num_results: The maximum number of results to return (1-10).

    Returns:
        A list of URLs found, or an empty list if an error occurs or no results found.
    """
    logger.info(f"Performing Google search for: '{query}' (requesting up to {num_results} results)")
    try:
        def _blocking_google_search():
            service = build("customsearch", "v1", developerKey=settings.GOOGLE_API_KEY)
            num = max(1, min(num_results, 10)) # Google's max per request is 10
            result = service.cse().list(
                q=query,
                cx=settings.GOOGLE_CSE_ID,
                num=num
            ).execute()
            return [item.get("link") for item in result.get("items", []) if item.get("link")]

        loop = asyncio.get_running_loop()
        urls = await loop.run_in_executor(None, _blocking_google_search)

        logger.info(f"Found {len(urls)} URLs via Google Search for query '{query}'.")
        return urls

    except HttpError as e:
        logger.error(f"Google Search API Error for query '{query}': {e.resp.status} {e.reason} - {e.content}")
        return []
    except Exception as e:
        logger.exception(f"An unexpected error occurred during Google search for query '{query}'") # Log full exception
        return []