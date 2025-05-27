# app/features/elasticsearch/service.py

import logging
from typing import List
# Corrected imports for Elasticsearch exceptions
from elasticsearch import Elasticsearch, ApiError, NotFoundError, ConnectionError, TransportError
from sqlalchemy.orm import Session

from app.features.elasticsearch.config import elasticsearch_settings
# Ensure this import path is correct for your project structure:
from app.db_connectors.models import Note # Or wherever your Note SQLAlchemy model is defined
from app.features.elasticsearch.helpers import build_es_document

logger = logging.getLogger(__name__)

class ElasticsearchService:
    def __init__(self):
        self.index_name = elasticsearch_settings.INDEX_NAME
        self.es_hosts_list = elasticsearch_settings.HOSTS_LIST # Assuming HOSTS_LIST from adjusted config
        self.es = None

        if not self.es_hosts_list:
            logger.error(
                "Elasticsearch hosts (HOSTS_LIST from elasticsearch_settings) are not configured or ES_HOST_URL is empty. "
                "Elasticsearch client will not be initialized."
            )
            return

        logger.info(f"Attempting to initialize Elasticsearch client with hosts: {self.es_hosts_list}")
        try:
            self.es = Elasticsearch(hosts=self.es_hosts_list)

            if not self.es.ping():
                logger.error(
                    f"Elasticsearch client initialized but FAILED to PING at {self.es_hosts_list}. "
                    "Check if Elasticsearch is running, accessible, and if the URLs are correct."
                )
                self.es = None
            else:
                logger.info(
                    f"ElasticsearchService successfully initialized and PINGED. "
                    f"Connected to Elasticsearch at {self.es_hosts_list} using index '{self.index_name}'."
                )
        except ValueError as ve:
            logger.error(
                f"ValueError during Elasticsearch client initialization with hosts {self.es_hosts_list}: {ve}. "
                "Ensure ES_HOST in core config is a complete URL (e.g., 'http://localhost:9200')."
            )
            self.es = None
        except (ConnectionError, TransportError) as e: # Catch specific connection/transport errors
            logger.error(
                f"Elasticsearch Connection/Transport Error during client initialization with hosts {self.es_hosts_list}: {type(e).__name__} - {e}"
            )
            self.es = None
        except Exception as e:
            logger.exception(
                f"An unexpected error occurred while initializing Elasticsearch client with hosts {self.es_hosts_list}."
            )
            self.es = None

    def _check_client(self) -> bool:
        if not self.es:
            logger.error("Elasticsearch client is not initialized or connection failed. Cannot perform operation.")
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
        except (ApiError, TransportError) as e: # Corrected exception handling
            logger.error(f"Elasticsearch API/Transport Error indexing Note {note_id}: {type(e).__name__} - {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected Python error indexing Note {note_id}: {e}")
            return False

    def search_notes(self, query: str) -> List[dict]:
        if not self._check_client():
            return []

        es_query = {
            "query": {
                "multi_match": {
                    "query": query,
                    "fields": ["title", "text"] # Adjust fields as necessary
                }
            }
        }
        try:
            result = self.es.search(index=self.index_name, body=es_query)
            hits_data = result.get("hits", {}).get("hits", [])
            hits = [hit["_source"] for hit in hits_data if "_source" in hit]
            logger.info(f"Elasticsearch search for '{query}' found {len(hits)} results.")
            return hits
        except NotFoundError: # Specific handling for index not found
            logger.warning(f"Search failed for query '{query}' because index '{self.index_name}' was not found.")
            return []
        except (ApiError, TransportError) as e: # Corrected exception handling for other ES errors
            logger.error(f"Elasticsearch API/Transport Error during search for query '{query}': {type(e).__name__} - {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected Python error during Elasticsearch search for query '{query}': {e}")
            return []

    def delete_note(self, note_id: int) -> bool:
        if not self._check_client():
            return False
        try:
            self.es.delete(index=self.index_name, id=str(note_id), refresh="wait_for")
            logger.info(f"Successfully deleted Note {note_id} from Elasticsearch.")
            return True
        except NotFoundError: # Specific handling for note or index not found
            logger.warning(f"Note {note_id} not found in Elasticsearch (or index '{self.index_name}' not found). Could not delete.")
            return False
        except (ApiError, TransportError) as e: # Corrected exception handling
            logger.error(f"Elasticsearch API/Transport Error deleting Note {note_id}: {type(e).__name__} - {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected Python error deleting Note {note_id} from Elasticsearch: {e}")
            return False