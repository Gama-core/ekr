import asyncio
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Tuple, Optional

from .config import settings
from .schemas import GoogleSearchResultItem

logger = logging.getLogger(__name__)


async def perform_google_search(
        query: str,
        num_results: int
) -> Tuple[List[GoogleSearchResultItem], Optional[str]]:
    """
    Performs a Google search using the google-api-python-client.
    Returns a tuple of (results, error_message).
    """
    if not all([settings.GOOGLE_API_KEY, settings.GOOGLE_CSE_ID]):
        error_msg = "Service is not configured with Google API credentials."
        logger.error(error_msg)
        return [], error_msg

    logger.info(f"Performing Google search for: '{query}' (requesting up to {num_results} results)")

    # The Google API call is synchronous, so we run it in a thread pool
    # to avoid blocking the main async event loop.
    def _blocking_api_call():
        service = build(
            "customsearch", "v1",
            developerKey=settings.GOOGLE_API_KEY.get_secret_value()
        )
        result = service.cse().list(
            q=query,
            cx=settings.GOOGLE_CSE_ID,
            num=num_results
        ).execute()
        return result.get("items", [])

    try:
        loop = asyncio.get_running_loop()
        search_items_raw = await loop.run_in_executor(None, _blocking_api_call)

        search_results: List[GoogleSearchResultItem] = [
            GoogleSearchResultItem.model_validate(item) for item in search_items_raw
        ]

        logger.info(f"Found {len(search_results)} results for query '{query}'.")
        return search_results, None

    except HttpError as e:
        error_msg = f"Google Search API Error: {e.resp.status} {e.reason}"
        logger.error(f"{error_msg} - Details: {e.content.decode('utf-8') if e.content else 'N/A'}")
        return [], error_msg
    except Exception as e:
        error_msg = f"Unexpected error during Google search: {type(e).__name__} - {e}"
        logger.exception(error_msg)
        return [], error_msg