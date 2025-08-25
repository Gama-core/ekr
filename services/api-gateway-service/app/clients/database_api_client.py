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
    """Fetches all notes for a user by streaming from the database-api."""
    notes = []
    url = f"{settings.DATABASE_API_URL}/notes/stream/by-user/{user_id}"
    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            async with client.stream("GET", url) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        note_data = json.loads(line)
                        if 'text_content' in note_data:
                            note_data['text'] = note_data.pop('text_content')
                        notes.append(NoteResponse.model_validate(note_data))
    except httpx.HTTPStatusError as e:
        logger.error(f"Error fetching notes for user {user_id}: {e.response.text}")
        raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")
    return notes

async def get_note_by_id_from_db(note_id: int) -> Optional[NoteResponse]:
    """Fetches a single note by its ID from the database-api."""
    url = f"{settings.DATABASE_API_URL}/notes/by-id/{note_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url)
            if response.status_code == status.HTTP_404_NOT_FOUND:
                return None
            response.raise_for_status()
            note_data = response.json()
            if 'text_content' in note_data:
                note_data['text'] = note_data.pop('text_content')
            return NoteResponse.model_validate(note_data)
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
            created_note = response.json()
            if 'text_content' in created_note:
                created_note['text'] = created_note.pop('text_content')
            return NoteResponse.model_validate(created_note)
        except httpx.HTTPStatusError as e:
            logger.error(f"Error creating note in DB: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")

async def update_note_in_db(note_id: int, payload: Dict[str, Any]) -> NoteResponse:
    """Sends a request to the database-api to update a note."""
    url = f"{settings.DATABASE_API_URL}/notes/{note_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.put(url, json=payload)
            response.raise_for_status()
            updated_note = response.json()
            if 'text_content' in updated_note:
                updated_note['text'] = updated_note.pop('text_content')
            return NoteResponse.model_validate(updated_note)
        except httpx.HTTPStatusError as e:
            logger.error(f"Error updating note {note_id} in DB: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")

async def delete_note_from_db(note_id: int) -> NoteResponse:
    """Sends a request to the database-api to delete a note."""
    url = f"{settings.DATABASE_API_URL}/notes/{note_id}"
    async with httpx.AsyncClient() as client:
        try:
            response = await client.delete(url)
            response.raise_for_status()
            deleted_note = response.json()
            if 'text_content' in deleted_note:
                deleted_note['text'] = deleted_note.pop('text_content')
            return NoteResponse.model_validate(deleted_note)
        except httpx.HTTPStatusError as e:
            logger.error(f"Error deleting note {note_id} from DB: {e.response.text}")
            raise HTTPException(status_code=e.response.status_code, detail=f"Database API error: {e.response.text}")