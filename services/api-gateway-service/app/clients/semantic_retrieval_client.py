# app/clients/semantic_retrieval_client.py
import logging
import httpx
from typing import Dict, Any, List

from fastapi import HTTPException, status
from ..config import settings

logger = logging.getLogger(__name__)

async def index_note(note_id: int):
    """Tells the semantic-retrieval service to index a new or updated note."""
    # FIX: Added the '/rag' prefix to match the router configuration in the semantic-retrieval service.
    url = f"{settings.SEMANTIC_RETRIEVAL_API_URL}/rag/index/note"
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
    # FIX: Added the '/rag' prefix here as well.
    url = f"{settings.SEMANTIC_RETRIEVAL_API_URL}/rag/index/note/{note_id}"
    try:
        async with httpx.AsyncClient() as client:
            response = await client.delete(url)
            response.raise_for_status()
        logger.info(f"Successfully triggered deletion from index for note_id: {note_id}")
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to delete note_id {note_id} from index. Status: {e.response.status_code}, Detail: {e.response.text}")

async def retrieve_context(query: str, user_id: int) -> List[Dict[str, Any]]:
    """Calls the semantic-retrieval service to get relevant note chunks."""
    # This URL is already correct as it was defined with the prefix in mind.
    url = f"{settings.SEMANTIC_RETRIEVAL_API_URL}/rag/retrieve"
    payload = {"query": query, "user_id": user_id}
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            response_data = response.json()
            return response_data.get("retrieved_items", [])
    except httpx.HTTPStatusError as e:
        logger.error(f"Failed to retrieve context for user {user_id}. Status: {e.response.status_code}, Detail: {e.response.text}")
        # Return an empty list on failure, as the chat can proceed without RAG context.
        return []
    except httpx.RequestError as e:
        logger.error(f"Could not connect to Semantic Retrieval Service at {url}: {e}")
        # Also return an empty list on connection errors.
        return []