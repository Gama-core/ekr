# app/clients/summary_client.py
import logging
import httpx
from typing import Dict, Any

from fastapi import HTTPException, status
from ..config import settings

logger = logging.getLogger(__name__)


async def generate_summary_for_note(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sends a request to the summary-service to generate a summary."""
    url = f"{settings.SUMMARY_API_URL}/summarize"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            response = await client.post(url, json=payload)

            # Check for specific downstream errors returned by the summary service
            if response.status_code == status.HTTP_502_BAD_GATEWAY:
                downstream_error = response.json().get("detail", "Unknown LLM service error")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=downstream_error)

            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Error generating summary: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Summary Service error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Could not connect to Summary Service at {url}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                            detail="The Summary Service is currently unavailable.")