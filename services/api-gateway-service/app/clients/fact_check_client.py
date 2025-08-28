# app/clients/fact_check_client.py
import logging
import httpx
from typing import Dict, Any

from fastapi import HTTPException, status
from ..config import settings

logger = logging.getLogger(__name__)

async def fact_check_note_data(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sends a request to the fact-check-service to analyze note data."""
    url = f"{settings.FACT_CHECK_API_URL}/fact-check"
    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code == status.HTTP_502_BAD_GATEWAY:
                downstream_error = response.json().get("detail", "Unknown LLM service error during fact-check")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=downstream_error)

            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Error during fact-check: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Fact-Check Service error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Could not connect to Fact-Check Service at {url}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The Fact-Check Service is currently unavailable.")