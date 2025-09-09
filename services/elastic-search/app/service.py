# /elastic-search/app/service.py
import logging
from typing import List, Optional

from elasticsearch import AsyncElasticsearch, ApiError, NotFoundError, ConnectionError
from elasticsearch.helpers import async_scan, async_bulk

# Use relative imports for modules in the same 'app' directory
from .config import settings
from .helpers import build_es_document
# Import the client from the 'clients' sub-package
from .clients.database_client import get_note_by_id, stream_all_notes

logger = logging.getLogger(__name__)

class ElasticsearchService:
    def __init__(self):
        self.index_name: str = settings.ES_INDEX_NAME
        self.es: Optional[AsyncElasticsearch] = None
        connection_params = {}
        if settings.ES_CLOUD_ID and settings.ES_API_KEY_ID and settings.ES_API_KEY:
            connection_params = {"cloud_id": settings.ES_CLOUD_ID, "api_key": (settings.ES_API_KEY_ID, settings.ES_API_KEY)}
        elif settings.ES_HOST_URL:
            connection_params = {"hosts": settings.HOSTS_LIST}
            if settings.ES_USERNAME and settings.ES_PASSWORD:
                connection_params["basic_auth"] = (settings.ES_USERNAME, settings.ES_PASSWORD)
        else:
            logger.error("No ES connection config found.")
            return
        try:
            self.es = AsyncElasticsearch(**connection_params, retry_on_timeout=True, max_retries=3)
        except Exception:
            logger.exception("Error initializing AsyncElasticsearch client.")

    # All other methods in this class remain the same...
    async def _check_client(self) -> bool:
        if not self.es: return False
        try:
            return await self.es.ping()
        except ConnectionError:
            return False

    async def index_note(self, note_id: int) -> bool:
        if not await self._check_client(): return False
        note = await get_note_by_id(note_id)
        if not note: return False
        es_doc = build_es_document(note)
        try:
            await self.es.index(index=self.index_name, id=str(note_id), document=es_doc, refresh="wait_for")
            return True
        except ApiError: return False

    async def search_notes(self, query: str) -> List[dict]:
        if not await self._check_client(): return []
        es_query = {"query": {"multi_match": {"query": query, "fields": ["title", "text"]}}}
        try:
            result = await self.es.search(index=self.index_name, body=es_query)
            return [hit["_source"] for hit in result.get("hits", {}).get("hits", [])]
        except (ApiError, NotFoundError): return []

    async def delete_note(self, note_id: int) -> bool:
        if not await self._check_client(): return False
        try:
            await self.es.delete(index=self.index_name, id=str(note_id), refresh="wait_for")
            return True
        except NotFoundError: return True
        except ApiError: return False

    async def repair_index(self) -> int:
        if not await self._check_client(): return 0
        try:
            es_ids = {hit['_id'] async for hit in async_scan(self.es, index=self.index_name, query={"query": {"match_all": {}}, "_source": False})}
            actions = [
                {"_op_type": "index", "_index": self.index_name, "_id": str(note.id), "_source": build_es_document(note)}
                async for note in stream_all_notes() if str(note.id) not in es_ids
            ]
            if not actions:
                logger.info("Index is already in sync.")
                return 0
            success_count, _ = await async_bulk(self.es, actions, refresh="wait_for")
            return success_count
        except Exception as e:
            logger.exception(f"Error during index repair: {e}")
            return 0