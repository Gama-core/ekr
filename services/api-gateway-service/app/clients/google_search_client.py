# app/clients/google_search_client.py
import logging
import httpx
from typing import List, Dict, Any

from fastapi import HTTPException
from ..config import settings

logger = logging.getLogger(__name__)

async def perform_search(query: str, num_results: int = 3) -> List[Dict[str, Any]]:
    """Sends a search request to the google-search-service."""
    url = f"{settings.GOOGLE_SEARCH_API_URL}/search"
    payload = {"query": query, "num_results": num_results}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
            logger.info(f"Google Search successful for query '{query}'. Found {len(data.get('results', []))} results.")
            return data.get("results", [])
    except httpx.HTTPStatusError as e:
        logger.error(f"Error performing Google search: {e.response.text}")
        # Return empty list on failure, chat can proceed without web context
        return []
    except httpx.RequestError as e:
        logger.error(f"Could not connect to Google Search Service at {url}: {e}")
        return []