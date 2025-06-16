# app/features/semantic_retrieval/llama_ops/__init__.py
import logging
from typing import Optional
from llama_index.core import VectorStoreIndex
from llama_index.vector_stores.faiss import FaissVectorStore

logger = logging.getLogger(__name__)

_vector_index_instance: Optional[VectorStoreIndex] = None
_faiss_vector_store_instance: Optional[FaissVectorStore] = None
_llama_settings_globally_initialized: bool = False


def set_global_vector_index(instance: Optional[VectorStoreIndex]):
    global _vector_index_instance
    _vector_index_instance = instance

def get_global_vector_index() -> Optional[VectorStoreIndex]:
    global _vector_index_instance
    return _vector_index_instance

def set_global_faiss_vector_store(instance: Optional[FaissVectorStore]):
    global _faiss_vector_store_instance
    _faiss_vector_store_instance = instance

def get_global_faiss_vector_store() -> Optional[FaissVectorStore]:
    global _faiss_vector_store_instance
    return _faiss_vector_store_instance

def set_llama_settings_initialized_flag(initialized: bool):
    global _llama_settings_globally_initialized
    _llama_settings_globally_initialized = initialized

def get_llama_settings_initialized_flag() -> bool:
    global _llama_settings_globally_initialized
    return _llama_settings_globally_initialized


from .embedding_setup import (
    initialize_llama_index_settings,
    db_note_to_llama_document
)

from .index_io import (
    ensure_faiss_vector_store_with_idmap,
    ensure_vector_index,
    persist_index_and_vector_store,
    clear_index_storage_completely,
    get_faiss_index_type_description
)

from .indexing_ops import (
    refresh_document_in_index,
    remove_document_from_index # For potential future direct delete endpoint
)

from .query_ops import (
    execute_query_against_index
)


def get_active_vector_index(recreate_faiss: bool = False) -> Optional[VectorStoreIndex]:
    initialize_llama_index_settings()
    return ensure_vector_index(recreate_faiss=recreate_faiss)

logger.info("Llama_ops package for semantic_retrieval initialized.")