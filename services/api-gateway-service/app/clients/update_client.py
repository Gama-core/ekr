# app/clients/update_client.py
import logging
import httpx
from typing import Dict, Any

from fastapi import HTTPException, status
from ..config import settings

logger = logging.getLogger(__name__)

async def update_note_content(payload: Dict[str, Any]) -> Dict[str, Any]:
    """Sends a request to the update-service to modify note content."""
    url = f"{settings.UPDATE_API_URL}/update"
    try:
        # The update process can be long, so a generous timeout is needed.
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(url, json=payload)

            if response.status_code == status.HTTP_502_BAD_GATEWAY:
                downstream_error = response.json().get("detail", "Unknown LLM service error during update")
                raise HTTPException(status_code=status.HTTP_502_BAD_GATEWAY, detail=downstream_error)

            response.raise_for_status()
            return response.json()
    except httpx.HTTPStatusError as e:
        logger.error(f"Error during note update: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Update Service error: {e.response.text}")
    except httpx.RequestError as e:
        logger.error(f"Could not connect to Update Service at {url}: {e}")
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="The Update Service is currently unavailable.")