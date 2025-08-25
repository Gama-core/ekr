# app/clients/semantic_retrieval_client.py
import logging
import httpx

from fastapi import HTTPException, status
from ..config import settings

logger = logging.getLogger(__name__)

async def index_note(note_id: int):
    """Tells the semantic-retrieval service to index a new or updated note."""
    url = f"{settings.SEMANTIC_RETRIEVAL_API_URL}/index/note"
    payload = {"note_id": note_id}
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
        logger.info(f"Successfully triggered indexing for note_id: {note_id}")
    except httpx.HTTPStatusError as e:
        # We log this as an error but don't re-raise HTTPException
        # The primary operation (DB write) succeeded, so we don't want to fail the whole request
        logger.error(f"Failed to index note_id {note_id}. Status: {e.response.status_code}, Detail: {e.response.text}")
        # In a production system, this failure would be sent to a retry queue.

async def delete_note_from_index(note_id: int):
    """Tells the semantic-retrieval service to remove a note from its index."""
    url = f"{settings.SEMANTIC_RETRIEVAL_API_URL}/index/note/{note_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(url)
            response.raise_for_status()
        logger.info(f"Successfully triggered deletion from index for note_id: {note_id}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to delete note_id {note_id} from index. Status: {e.response.status_code}, Detail: {e.response.text}")