# app/services/google_search.py

import asyncio
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from app.core.config import settings # Import config to get API keys

async def search_web(query: str, num_results: int = 5) -> list[str]:
    """
    Performs a web search using the Google Custom Search JSON API.

    Args:
        query: The search term.
        num_results: The maximum number of results to return (1-10).

    Returns:
        A list of URLs found, or an empty list if an error occurs or no results found.
    """
    print(f"Performing Google search for: '{query}' ({num_results} results)")
    try:
        # Define the synchronous blocking function that uses the Google library
        def _blocking_google_search():
            service = build("customsearch", "v1", developerKey=settings.GOOGLE_API_KEY)
            # Ensure num is within Google's allowed range (1-10) for a single request
            num = max(1, min(num_results, 10))
            result = service.cse().list(
                q=query,
                cx=settings.GOOGLE_CSE_ID,
                num=num
            ).execute()
            # Extract the 'link' field from each item, handling cases where 'items' might be missing
            return [item.get("link") for item in result.get("items", []) if item.get("link")]

        # Run the blocking function in FastAPI's default thread pool
        loop = asyncio.get_running_loop()
        urls = await loop.run_in_executor(None, _blocking_google_search) # None uses the default executor

        print(f"Found {len(urls)} URLs via Google Search.")
        return urls

    except HttpError as e:
        # Handle API-specific errors (e.g., invalid key, quota exceeded)
        print(f"Google Search API Error: {e.resp.status} {e.reason} - {e.content}")
        # You might want to raise a specific custom exception here
        return [] # Return empty list on error
    except Exception as e:
        # Handle other unexpected errors
        print(f"An unexpected error occurred during Google search: {type(e).__name__} - {e}")
        # Consider logging the full traceback here
        return [] # Return empty list on error