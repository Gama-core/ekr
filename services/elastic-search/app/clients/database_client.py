# services/elasticsearch-service/app/features/elasticsearch/database_client.py
import logging
import httpx
import json
from typing import Optional, AsyncGenerator

from app.config import settings
from app.schemas import NoteForIndex

logger = logging.getLogger(__name__)

if not settings.DATABASE_API_URL:
    logger.critical("DATABASE_API_URL not set. DatabaseClient cannot be initialized.")
    _client = None
else:
    _client = httpx.AsyncClient(base_url=settings.DATABASE_API_URL, timeout=60.0)

async def get_note_by_id(note_id: int) -> Optional[NoteForIndex]:
    """Fetches a single note from the database-api service."""
    if not _client: return None
    try:
        response = await _client.get(f"/notes/{note_id}")
        if response.status_code == 404:
            logger.warning(f"Note ID {note_id} not found via Database API.")
            return None
        response.raise_for_status()
        return NoteForIndex(**response.json())
    except httpx.RequestError as e:
        logger.error(f"HTTP client error fetching note {note_id}: {e}")
        return None
    except Exception as e:
        logger.exception(f"Error processing response for note {note_id}: {e}")
        return None

async def stream_all_notes() -> AsyncGenerator[NoteForIndex, None]:
    """Streams all notes from the database-api service."""
    if not _client:
        return
    try:
        async with _client.stream("GET", "/notes/stream/all") as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    yield NoteForIndex(**json.loads(line))
    except httpx.RequestError as e:
        logger.error(f"HTTP client error while streaming notes: {e}")
    except Exception as e:
        logger.exception(f"Error processing streamed notes: {e}")