# app/clients/web_crawl_client.py
import logging
import httpx
from typing import List, Dict, Any

from ..config import settings

logger = logging.getLogger(__name__)

async def crawl_urls(urls: List[str]) -> List[Dict[str, Any]]:
    """Sends a list of URLs to the web-crawl-service."""
    if not urls:
        return []
    url = f"{settings.WEB_CRAWL_API_URL}/multiple-urls"
    payload = {"urls": urls}
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            results = response.json()
            logger.info(f"Web Crawl successful for {len(results)} URLs.")
            return results
    except httpx.HTTPStatusError as e:
        logger.error(f"Error during web crawl: {e.response.text}")
        return []
    except httpx.RequestError as e:
        logger.error(f"Could not connect to Web Crawl Service at {url}: {e}")
        return []