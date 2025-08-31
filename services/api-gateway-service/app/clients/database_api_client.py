# app/clients/database_api_client.py
import logging
import httpx
import json
from typing import List, Optional, Dict, Any

from fastapi import HTTPException, status
from ..config import settings
from ..schemas.note_schemas import NoteResponse

logger = logging.getLogger(__name__)

async def get_notes_for_user(user_id: int) -> List[NoteResponse]:
    """Fetches all notes for a user from the database-api using a standard GET request."""
    url = f"{settings.DATABASE_API_URL}/notes/by-user/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(url)
            response.raise_for_status()
            note_list = response.json()
            notes = [NoteResponse.model_validate(note_data) for note_data in note_list]
            return notes
    except httpx.HTTPStatusError as e:
        logger.error(f"Error fetching notes for user {user_id}: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")
    except (json.JSONDecodeError, TypeError) as e:
        logger.error(f"Error decoding JSON response from database-api for user {user_id}: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Invalid response from database service.")

async def get_note_by_id_from_db(note_id: int) -> Optional[NoteResponse]:
    """Fetches a single note by its ID from the database-api."""
    url = f"{settings.DATABASE_API_URL}/notes/by-id/{note_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == status.HTTP_404_NOT_FOUND:
                return None
            response.raise_for_status()
            return NoteResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"Error fetching note {note_id}: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")

async def create_note_in_db(payload: Dict[str, Any]) -> NoteResponse:
    """Sends a request to the database-api to create a new note."""
    url = f"{settings.DATABASE_API_URL}/notes"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, json=payload)
            response.raise_for_status()
            return NoteResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating note in DB: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")

# --- FIX #1: Restored the missing update_note_in_db function ---
async def update_note_in_db(note_id: int, payload: Dict[str, Any]) -> NoteResponse:
    """Sends a request to the database-api to update a note."""
    url = f"{settings.DATABASE_API_URL}/notes/{note_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, json=payload)
            response.raise_for_status()
            return NoteResponse.model_validate(response.json())
        except httpx.HTTPStatusError as e:
            logger.error(f"Error updating note {note_id} in DB: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")

# --- FIX #2: This function now correctly handles the 204 No Content response ---
async def delete_note_from_db(note_id: int) -> None:
    """Sends a request to the database-api to delete a note."""
    url = f"{settings.DATABASE_API_URL}/notes/{note_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url)
            response.raise_for_status()
            # We no longer expect a body, so we do not call response.json()
        except httpx.HTTPStatusError as e:
            logger.error(f"Error deleting note {note_id} from DB: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")