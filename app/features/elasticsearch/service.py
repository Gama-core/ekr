# app/features/elasticsearch/service.py

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
        is_cloud_connection = False # Flag to check if it's a cloud_id connection

        # --- Determine Connection Method ---
        # Priority 1: Elastic Cloud ID and API Key
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
            is_cloud_connection = True # Set the flag

        # Priority 2: ES_HOST_URL (e.g., for AWS OpenSearch, self-managed, or direct Elastic Cloud endpoint)
        elif elasticsearch_settings.ES_HOST_URL:
            self.es_hosts_list: List[str] = elasticsearch_settings.HOSTS_LIST
            if not self.es_hosts_list:
                logger.error(
                    "ES_HOST_URL is configured but HOSTS_LIST is empty. "
                    "Elasticsearch client will not be initialized."
                )
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
            logger.error(
                "Elasticsearch connection details (neither ES_CLOUD_ID/API_KEY nor ES_HOST_URL) "
                "are sufficiently configured. Elasticsearch client will not be initialized."
            )
            return 

        # --- Attempt Connection ---
        try:
            # Only add timeout and retry_on_timeout if NOT using cloud_id
            # and if connecting via hosts (Priority 2)
            if not is_cloud_connection and "hosts" in connection_params:
                connection_params["timeout"] = 30
                connection_params["retry_on_timeout"] = True
            
            self.es = Elasticsearch(**connection_params)

            if not self.es.ping():
                logger.error(
                    f"Elasticsearch client initialized but FAILED to PING using {connection_type}. "
                    "Check connection details, network access, service status, and authentication."
                )
                self.es = None
            else:
                logger.info(
                    f"ElasticsearchService successfully initialized and PINGED. "
                    f"Connected to Elasticsearch via {connection_type} using index '{self.index_name}'."
                )
        except ValueError as ve: 
            logger.error(
                f"ValueError during Elasticsearch client initialization ({connection_type}): {ve}. "
                "Ensure ES_HOST_URL (if used) is a complete URL (e.g., 'https://...')."
            )
            self.es = None
        except (ConnectionError, TransportError) as e: 
            logger.error(
                f"Elasticsearch Connection/Transport Error during client initialization ({connection_type}): {type(e).__name__} - {e}"
            )
            self.es = None
        except ApiError as ae: 
             logger.error(
                f"Elasticsearch API Error during client initialization or ping ({connection_type}): {type(ae).__name__} - {ae}. "
                "Check API Key permissions or username/password if using basic auth."
            )
             self.es = None
        # Catch TypeError specifically for unexpected keyword arguments
        except TypeError as te:
            logger.error(
                f"TypeError during Elasticsearch client initialization ({connection_type}): {te}. "
                "This might indicate an unsupported parameter for the chosen connection method."
            )
            self.es = None
        except Exception as e: 
            logger.exception(
                f"An unexpected error occurred while initializing Elasticsearch client ({connection_type})."
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
            if self.es:
                self.es.index(index=self.index_name, id=str(note_id), document=es_doc, refresh="wait_for")
                logger.info(f"Successfully indexed Note {note_id} to Elasticsearch.")
                return True
            else: 
                logger.error("Cannot index note: Elasticsearch client (self.es) is None.")
                return False
        except (ApiError, TransportError) as e:
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
                    "fields": ["title", "text"] 
                }
            }
        }
        try:
            if self.es:
                result = self.es.search(index=self.index_name, body=es_query)
                hits_data = result.get("hits", {}).get("hits", [])
                hits = [hit["_source"] for hit in hits_data if hit.get("_source") is not None]
                logger.info(f"Elasticsearch search for '{query}' found {len(hits)} results.")
                return hits
            else: 
                logger.error("Cannot search notes: Elasticsearch client (self.es) is None.")
                return []
        except NotFoundError:
            logger.warning(f"Search failed for query '{query}' because index '{self.index_name}' was not found.")
            return []
        except (ApiError, TransportError) as e:
            logger.error(f"Elasticsearch API/Transport Error during search for query '{query}': {type(e).__name__} - {e}")
            return []
        except Exception as e:
            logger.exception(f"Unexpected Python error during Elasticsearch search for query '{query}': {e}")
            return []

    def delete_note(self, note_id: int) -> bool:
        if not self._check_client():
            return False
        try:
            if self.es:
                self.es.delete(index=self.index_name, id=str(note_id), refresh="wait_for")
                logger.info(f"Successfully deleted Note {note_id} from Elasticsearch.")
                return True
            else: 
                logger.error("Cannot delete note: Elasticsearch client (self.es) is None.")
                return False
        except NotFoundError:
            logger.warning(f"Note {note_id} not found in Elasticsearch (or index '{self.index_name}' not found). Could not delete.")
            return False 
        except (ApiError, TransportError) as e:
            logger.error(f"Elasticsearch API/Transport Error deleting Note {note_id}: {type(e).__name__} - {e}")
            return False
        except Exception as e:
            logger.exception(f"Unexpected Python error deleting Note {note_id} from Elasticsearch: {e}")
            return False