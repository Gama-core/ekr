import logging
from typing import Optional
from llama_index.core import VectorStoreIndex
from .custom_faiss_vstore import CustomFaissVectorStore

logger = logging.getLogger(__name__)

_vector_index_instance: Optional[VectorStoreIndex] = None
_faiss_vector_store_instance: Optional[CustomFaissVectorStore] = None
_llama_settings_globally_initialized: bool = False

def set_global_vector_index(instance: Optional[VectorStoreIndex]):
    global _vector_index_instance
    _vector_index_instance = instance

def get_global_vector_index() -> Optional[VectorStoreIndex]:
    global _vector_index_instance
    return _vector_index_instance

def set_global_faiss_vector_store(instance: Optional[CustomFaissVectorStore]):
    global _faiss_vector_store_instance
    _faiss_vector_store_instance = instance

def get_global_faiss_vector_store() -> Optional[CustomFaissVectorStore]:
    global _faiss_vector_store_instance
    return _faiss_vector_store_instance

def set_llama_settings_initialized_flag(initialized: bool):
    global _llama_settings_globally_initialized
    _llama_settings_globally_initialized = initialized

def get_llama_settings_initialized_flag() -> bool:
    global _llama_settings_globally_initialized
    return _llama_settings_globally_initialized

from .embedding_setup import initialize_llama_index_settings, db_note_to_llama_document
from .index_io import ensure_faiss_vector_store_with_idmap, ensure_vector_index, persist_index_and_vector_store, clear_index_storage_completely, get_faiss_index_type_description
from .indexing_ops import refresh_document_in_index, remove_document_from_index
from .query_ops import execute_query_against_index

def get_active_vector_index(recreate_faiss: bool = False) -> Optional[VectorStoreIndex]:
    initialize_llama_index_settings()
    return ensure_vector_index(recreate_faiss=recreate_faiss)