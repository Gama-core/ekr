# app/clients/database_client.py
import logging
import httpx
import json
from typing import Optional, AsyncGenerator
from urllib.parse import urljoin

# CHANGED: Use relative imports to go up one level to the 'app' package
from ..schemas import NoteForIndex
from ..config import settings

logger = logging.getLogger(__name__)

class DatabaseAPIClient:
    def __init__(self, base_url: str):
        self.base_url = base_url
        self.client = httpx.AsyncClient(timeout=60.0)
        logger.info(f"DatabaseAPIClient initialized for base URL: {self.base_url}")

    async def get_note_by_id(self, note_id: int) -> Optional[NoteForIndex]:
        """Fetches a single note by its ID from the database-api."""
        url = urljoin(self.base_url, f"notes/{note_id}")
        try:
            response = await self.client.get(url)
            if response.status_code == 404:
                logger.warning(f"Note with ID {note_id} not found via database-api.")
                return None
            response.raise_for_status()
            return NoteForIndex(**response.json())
        except httpx.RequestError as e:
            logger.error(f"Error requesting note {note_id} from database-api: {e}")
            return None
        except Exception as e:
            logger.exception(f"Failed to process response for note {note_id}: {e}")
            return None

    async def stream_all_notes(self) -> AsyncGenerator[NoteForIndex, None]:
        """Streams all notes from the database-api's NDJSON endpoint."""
        url = urljoin(self.base_url, "notes/stream/all")
        try:
            async with self.client.stream("GET", url) as response:
                response.raise_for_status()
                async for line in response.aiter_lines():
                    if line:
                        try:
                            note_data = json.loads(line)
                            yield NoteForIndex(**note_data)
                        except json.JSONDecodeError:
                            logger.warning(f"Failed to decode NDJSON line: {line}")
        except httpx.RequestError as e:
            logger.error(f"Error streaming notes from database-api: {e}")
            raise RuntimeError(f"Could not connect to database-api stream at {url}") from e

# Create a global instance for the service to use
database_client = DatabaseAPIClient(base_url=str(settings.DATABASE_API_URL))