import logging
from typing import List, Optional
from elasticsearch import Elasticsearch, ApiError, NotFoundError, ConnectionError, TransportError
from sqlalchemy.orm import Session

from app.features.elasticsearch.config import elasticsearch_settings
from app.db_connectors.models import Note
from app.features.elasticsearch.helpers import build_es_document

logger = logging.getLogger(__name__)

class ElasticsearchService:
    def __init__(self):
        self.index_name: str = elasticsearch_settings.INDEX_NAME
        self.es: Optional[Elasticsearch] = None

        connection_params = {}
        connection_type = "None"
        is_cloud_connection = False

        # --- Determine Connection Method ---
        if elasticsearch_settings.ES_CLOUD_ID and \
           elasticsearch_settings.ES_API_KEY_ID and \
           elasticsearch_settings.ES_API_KEY:
            logger.info(
                f"Attempting to initialize Elasticsearch client using Elastic Cloud ID: "
                f"{elasticsearch_settings.ES_CLOUD_ID[:15]}... and API Key ID."
            )
            connection_params = {
                "cloud_id": elasticsearch_settings.ES_CLOUD_ID,
                "api_key": (elasticsearch_settings.ES_API_KEY_ID, elasticsearch_settings.ES_API_KEY)
            }
            connection_type = f"Elastic Cloud (ID: {elasticsearch_settings.ES_CLOUD_ID[:15]}...)"
            is_cloud_connection = True

        elif elasticsearch_settings.ES_HOST_URL:
            self.es_hosts_list: List[str] = elasticsearch_settings.HOSTS_LIST
            if not self.es_hosts_list:
                logger.error("ES_HOST_URL is configured but HOSTS_LIST is empty.")
                return

            logger.info(f"Attempting to initialize Elasticsearch client with hosts: {self.es_hosts_list}")
            connection_params = {"hosts": self.es_hosts_list}
            connection_type = f"Direct Host(s): {self.es_hosts_list}"

            if elasticsearch_settings.ES_USERNAME and elasticsearch_settings.ES_PASSWORD:
                connection_params["basic_auth"] = (
                    elasticsearch_settings.ES_USERNAME,
                    elasticsearch_settings.ES_PASSWORD
                )
                logger.info(f"Using Basic Auth with username: {elasticsearch_settings.ES_USERNAME}")
                connection_type += f" (with Basic Auth User: {elasticsearch_settings.ES_USERNAME})"

        else:
            logger.error("No valid Elasticsearch connection config found. Initialization aborted.")
            return

        # --- Attempt Connection ---
        try:
            if not is_cloud_connection and "hosts" in connection_params:
                connection_params["timeout"] = 30
                connection_params["retry_on_timeout"] = True

            self.es = Elasticsearch(**connection_params)

            if not self.es.ping():
                logger.error(
                    f"Elasticsearch client initialized but FAILED to PING using {connection_type}."
                )
                self.es = None
            else:
                logger.info(
                    f"ElasticsearchService successfully initialized and PINGED. "
                    f"Connected via {connection_type}, index: '{self.index_name}'."
                )
        except ValueError as ve:
            logger.error(f"ValueError during initialization ({connection_type}): {ve}")
            self.es = None
        except (ConnectionError, TransportError) as e:
            logger.error(f"Transport/Connection error during initialization ({connection_type}): {e}")
            self.es = None
        except ApiError as ae:
            logger.error(f"API error during initialization ({connection_type}): {ae}")
            self.es = None
        except TypeError as te:
            logger.error(f"TypeError during Elasticsearch init ({connection_type}): {te}")
            self.es = None
        except Exception as e:
            logger.exception(f"Unexpected error initializing Elasticsearch client ({connection_type}).")
            self.es = None

    def _check_client(self) -> bool:
        if not self.es:
            logger.error("Elasticsearch client is not initialized or connection failed.")
            return False
        return True

    def index_note(self, db: Session, note_id: int) -> bool:
        if not self._check_client():
            return False

        note = db.query(Note).filter(Note.id == note_id).first()
        if not note:
            logger.warning(f"Note {note_id} not found in DB. Cannot index.")
            return False

        es_doc = build_es_document(note)
        try:
            self.es.index(index=self.index_name, id=str(note_id), document=es_doc, refresh="wait_for")
            logger.info(f"Successfully indexed Note {note_id} to Elasticsearch.")
            return True
        except (ApiError, TransportError) as e:
            logger.error(f"Elasticsearch error indexing Note {note_id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error indexing Note {note_id}: {e}")
            return False

    def search_notes(self, query: str) -> List[dict]:
        if not self._check_client():
            return []

        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "text"]
                }
            }
        }

        try:
            result = self.es.search(index=self.index_name, body=es_query)
            hits_data = result.get("hits", {}).get("hits", [])
            hits = [hit["_source"] for hit in hits_data if "_source" in hit]
            logger.info(f"Search for '{query}' returned {len(hits)} hits.")
            return hits
        except NotFoundError:
            logger.warning(f"Index '{self.index_name}' not found.")
            return []
        except (ApiError, TransportError) as e:
            logger.error(f"Elasticsearch error during search: {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected error during search: {e}")
            return []

    def delete_note(self, note_id: int) -> bool:
        if not self._check_client():
            return False

        try:
            self.es.delete(index=self.index_name, id=str(note_id), refresh="wait_for")
            logger.info(f"Note {note_id} deleted from Elasticsearch.")
            return True
        except NotFoundError:
            logger.warning(f"Note {note_id} not found in index '{self.index_name}'.")
            return False
        except (ApiError, TransportError) as e:
            logger.error(f"Elasticsearch error deleting Note {note_id}: {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected error deleting Note {note_id}: {e}")
            return False

    def repair_index(self, db: Session) -> int:
        """
        Maintenance: Check all notes in DB and re-index those missing in Elasticsearch.
        Returns number of notes reindexed.
        """
        if not self._check_client():
            return 0

        reindexed_count = 0
        notes = db.query(Note).all()

        for note in notes:
            try:
                exists = self.es.exists(index=self.index_name, id=str(note.id))
                if not exists:
                    es_doc = build_es_document(note)
                    self.es.index(index=self.index_name, id=str(note.id), document=es_doc, refresh="wait_for")
                    reindexed_count += 1
                    logger.info(f"Reindexed missing note {note.id}")
            except Exception as e:
                logger.error(f"Failed to reindex note {note.id}: {e}")

        logger.info(f"Repair completed. {reindexed_count} notes reindexed.")
        return reindexed_count
