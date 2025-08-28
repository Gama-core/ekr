# app/clients/llm_query_client.py
import logging
import httpx
from typing import Dict, Any

from fastapi import HTTPException, status
from ..config import settings

logger = logging.getLogger(__name__)


async def query_llm(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sends a request to the llm-query-service."""
    url = f"{settings.LLM_QUERY_SERVICE_URL}/query"
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload)

            # The llm-query service might return its own errors
            if response.status_code >= 400:
                error_detail = response.json().get("detail", "Unknown LLM service error")
                raise HTTPException(status_code=response.status_code, detail=error_detail)

            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Error querying LLM: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"LLM Query Service error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Could not connect to LLM Query Service at {url}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="The LLM Query Service is currently unavailable.")