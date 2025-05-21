# app/features/web_interaction/google_search_service.py
import asyncio
import logging
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from typing import List, Tuple, Optional # Added Optional

# Import global and feature-specific configurations/schemas.
from app.core.config import settings
from app.features.web_interaction.schemas import GoogleSearchResultItem
from app.features.web_interaction.config import web_interaction_settings

logger = logging.getLogger(__name__)

# Performs a Google search using the Custom Search JSON API.
async def perform_google_search(
    query: str,
    num_results: int = web_interaction_settings.DEFAULT_NUM_GOOGLE_RESULTS
) -> Tuple[List[GoogleSearchResultItem], Optional[str]]:
    logger.info(f"Performing Google search for: '{query}' (requesting up to {num_results} results)")
    try:
        actual_num_results = max(1, min(num_results, 10)) # Ensure num_results is within API limits.

        # Blocking Google API call executed in a separate thread.
        def _blocking_google_search_api_call():
            service = build("customsearch", "v1", developerKey=settings.GOOGLE_API_KEY)
            result = service.cse().list(q=query, cx=settings.GOOGLE_CSE_ID, num=actual_num_results).execute()
            return result.get("items", [])

        loop = asyncio.get_running_loop()
        search_items_raw = await loop.run_in_executor(None, _blocking_google_search_api_call)

        search_results: List[GoogleSearchResultItem] = []
        if search_items_raw:
            for item_raw in search_items_raw:
                search_results.append(
                    GoogleSearchResultItem(
                        title=item_raw.get("title"),
                        link=item_raw.get("link"),
                        snippet=item_raw.get("snippet")
                    )
                )
        logger.info(f"Found {len(search_results)} results for query '{query}'.")
        return search_results, None # Return results and no error.

    except HttpError as e:
        error_msg = f"Google Search API Error: {e.resp.status} {e.reason} - {e.content.decode() if e.content else 'N/A'}"
        logger.error(f"{error_msg} (Query: '{query}')")
        return [], error_msg # Return empty list and error message.
    except Exception as e:
        error_msg = f"Unexpected error during Google search: {type(e).__name__} - {str(e)}"
        logger.exception(f"{error_msg} (Query: '{query}')")
        return [], error_msg # Return empty list and error message.