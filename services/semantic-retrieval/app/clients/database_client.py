import logging
import httpx
import json
from typing import Optional, AsyncGenerator

# Use relative imports within the same service app
from ..config import settings
from ..schemas import NoteForIndex

logger = logging.getLogger(__name__)

# A single, reusable async client instance is more efficient.
# It's configured once when the module is loaded.
_client = httpx.AsyncClient(base_url=settings.DATABASE_API_URL, timeout=30.0)


async def get_note_by_id(note_id: int) -> Optional[NoteForIndex]:
    """
    Fetches a single note by its ID from the database-api service.

    This function handles the HTTP request, status code checking, and response parsing.

    Returns:
        The note as a Pydantic model, or None if not found or on error.
    """
    try:
        logger.debug(f"Client: Requesting note ID {note_id} from {settings.DATABASE_API_URL}")
        response = await _client.get(f"/notes/by-id/{note_id}")

        if response.status_code == 404:
            logger.warning(f"Client: Note ID {note_id} not found via Database API (404).")
            return None

        # Raise an exception for other bad status codes (5xx, etc.)
        response.raise_for_status()

        # Validate the received data against our schema
        return NoteForIndex(**response.json())

    except httpx.RequestError as e:
        logger.error(f"HTTP client error fetching note {note_id}: {e}")
        return None
    except Exception as e:
        # This could be a JSON decoding error or a Pydantic validation error
        logger.error(f"Unexpected error processing response for note {note_id}: {e}")
        return None


async def stream_all_notes() -> AsyncGenerator[NoteForIndex, None]:
    """
    Streams all notes from the database-api service.

    This function handles the streaming connection and yields Pydantic NoteForIndex objects.
    """
    try:
        logger.debug(f"Client: Streaming all notes from {settings.DATABASE_API_URL}")
        async with _client.stream("GET", "/notes/stream/all") as response:
            response.raise_for_status()
            async for line in response.aiter_lines():
                if line:
                    note_data = json.loads(line)
                    yield NoteForIndex(**note_data)
    except httpx.RequestError as e:
        logger.error(f"HTTP client error while streaming all notes: {e}")
        # The generator will simply stop, which is acceptable behavior.
    except Exception as e:
        logger.error(f"Unexpected error processing streamed notes: {e}")