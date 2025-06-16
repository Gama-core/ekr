import logging
import httpx
import json
from typing import Optional, AsyncGenerator

from ..config import settings
from ..schemas import NoteForIndex

logger = logging.getLogger(__name__)

_client = httpx.AsyncClient(base_url=settings.DATABASE_API_URL, timeout=30.0)

async def get_note_by_id(note_id: int) -> Optional[NoteForIndex]:
    """Fetches a single note by its ID from the database-api service."""
    try:
        logger.debug(f"Client: Requesting note ID {note_id} from {settings.DATABASE_API_URL}")
        response = await _client.get(f"/notes/by-id/{note_id}")
        if response.status_code == 404:
            logger.warning(f"Client: Note ID {note_id} not found via Database API (404).")
            return None
        response.raise_for_status()
        return NoteForIndex(**response.json())
    except httpx.RequestError as e:
        logger.error(f"HTTP client error fetching note {note_id}: {e}")
        return None
    except Exception as e:
        logger.error(f"Error processing response for note {note_id}: {e}")
        return None

async def stream_all_notes() -> AsyncGenerator[NoteForIndex, None]:
    """Streams all notes from the database-api service."""
    try:
        logger.debug(f"Client: Streaming all notes from {settings.DATABASE_API_URL}")
        async with _client.stream("GET", "/notes/stream/all") as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield NoteForIndex(**json.loads(line))
    except httpx.RequestError as e:
        logger.error(f"HTTP client error while streaming all notes: {e}")
    except Exception as e:
        logger.error(f"Error processing streamed notes: {e}")