import logging
from typing import Optional, cast
import faiss
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings as LlamaSettings,
)
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

from .custom_faiss_vstore import CustomFaissVectorStore, MAPPINGS_FILENAME
from ..config import settings
from . import (
    get_global_faiss_vector_store, set_global_faiss_vector_store,
    get_global_vector_index, set_global_vector_index,
    initialize_llama_index_settings
)

logger = logging.getLogger(__name__)


def ensure_faiss_vector_store_with_idmap(recreate: bool = False) -> CustomFaissVectorStore:
    global_faiss_store_obj = get_global_faiss_vector_store()
    initialize_llama_index_settings()

    faiss_index_physical_path = settings.VECTOR_STORE_PATH / settings.FAISS_INDEX_FILENAME_DEFAULT
    embedding_dim = settings.ACTIVE_EMBEDDING_DIMENSION
    vector_store_persist_path_str = str(settings.VECTOR_STORE_PATH.resolve())

    if global_faiss_store_obj and isinstance(global_faiss_store_obj, CustomFaissVectorStore) and not recreate:
        if not global_faiss_store_obj._faiss_index:
            logger.warning("Llama_ops: Global CustomFaissVectorStore has no _faiss_index. Recreating.")
            recreate = True
        elif not isinstance(global_faiss_store_obj._faiss_index, faiss.IndexIDMap2):
            logger.warning(
                f"Llama_ops: Global FAISS store (Custom) _faiss_index is not IndexIDMap2. Forcing recreation.")
            recreate = True
        elif hasattr(global_faiss_store_obj._faiss_index,
                     'index') and global_faiss_store_obj._faiss_index.index.d != embedding_dim:
            actual_dim = global_faiss_store_obj._faiss_index.index.d
            logger.warning(
                f"Llama_ops: Global FAISS store dimension ({actual_dim}) differs from config ({embedding_dim}). Forcing recreation.")
            recreate = True

        if not recreate:
            return global_faiss_store_obj

    if recreate:
        logger.info("Llama_ops: Recreating FAISS vector store with IndexIDMap2.")
        mapping_file_to_clear = settings.VECTOR_STORE_PATH / MAPPINGS_FILENAME
        if mapping_file_to_clear.exists():
            mapping_file_to_clear.unlink(missing_ok=True)
        set_global_faiss_vector_store(None)

    faiss_idmap2_index: faiss.IndexIDMap2
    if faiss_index_physical_path.exists() and not recreate:
        try:
            loaded_raw_faiss_index = faiss.read_index(str(faiss_index_physical_path))
            if not isinstance(loaded_raw_faiss_index, faiss.IndexIDMap2) or (
                    hasattr(loaded_raw_faiss_index, 'index') and loaded_raw_faiss_index.index.d != embedding_dim):
                raise ValueError("Loaded index is not a valid IndexIDMap2 or has mismatched dimensions.")
            faiss_idmap2_index = cast(faiss.IndexIDMap2, loaded_raw_faiss_index)
            logger.info(f"Llama_ops: FAISS IndexIDMap2 loaded with {faiss_idmap2_index.ntotal} vectors.")
        except Exception as e:
            logger.warning(f"Llama_ops: Failed to load FAISS index ({e}). Creating new one.")
            flat_index = faiss.IndexFlatL2(embedding_dim)
            faiss_idmap2_index = faiss.IndexIDMap2(flat_index)
    else:
        logger.info(f"Llama_ops: Creating new FAISS IndexFlatL2 wrapped in IndexIDMap2 (dim: {embedding_dim}).")
        flat_index = faiss.IndexFlatL2(embedding_dim)
        faiss_idmap2_index = faiss.IndexIDMap2(flat_index)

    new_custom_faiss_store = CustomFaissVectorStore(
        faiss_index=faiss_idmap2_index,
        persist_path=vector_store_persist_path_str
    )
    set_global_faiss_vector_store(new_custom_faiss_store)
    return new_custom_faiss_store


def ensure_vector_index(recreate_faiss: bool = False) -> VectorStoreIndex:
    if recreate_faiss:
        clear_index_storage_completely()

    current_vector_index = get_global_vector_index()
    if current_vector_index and not recreate_faiss:
        return current_vector_index

    vector_store = ensure_faiss_vector_store_with_idmap(recreate=recreate_faiss)
    storage_context_path = settings.VECTOR_STORE_PATH

    try:
        if not (storage_context_path / "docstore.json").exists():
            logger.info("Llama_ops: Initializing new LlamaIndex VectorStoreIndex structure.")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            new_index = VectorStoreIndex.from_documents([], storage_context=storage_context)
            persist_index_and_vector_store(new_index, vector_store)
        else:
            logger.info(f"Llama_ops: Loading VectorStoreIndex from storage: {storage_context_path}")
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                persist_dir=str(storage_context_path)
            )
            new_index = load_index_from_storage(storage_context)
            new_index._vector_store = vector_store
            logger.info(f"Llama_ops: Successfully loaded VectorStoreIndex.")
    except Exception as e:
        logger.error(f"Llama_ops: Error loading/initializing index: {e}. Recreating from scratch.", exc_info=True)
        return ensure_vector_index(recreate_faiss=True)

    set_global_vector_index(new_index)
    return new_index


def persist_index_and_vector_store(index_to_persist: Optional[VectorStoreIndex],
                                   vector_store_to_persist: Optional[CustomFaissVectorStore]):
    if not index_to_persist or not vector_store_to_persist or not vector_store_to_persist._faiss_index:
        logger.error("Llama_ops: Cannot persist index, one or more components are None.")
        return

    try:
        persist_dir = settings.VECTOR_STORE_PATH
        index_to_persist.storage_context.persist(persist_dir=str(persist_dir))
        faiss_idx_path = persist_dir / settings.FAISS_INDEX_FILENAME_DEFAULT
        faiss.write_index(vector_store_to_persist._faiss_index, str(faiss_idx_path))
        vector_store_to_persist._save_mappings()
        logger.info(f"Llama_ops: Index persisted successfully to {persist_dir}")
    except Exception as e:
        logger.exception(f"Llama_ops: Error during index persistence: {e}")


def clear_index_storage_completely():
    logger.info("Llama_ops: Clearing all files in VECTOR_STORE_PATH...")
    vector_store_dir = settings.VECTOR_STORE_PATH
    if vector_store_dir.exists():
        for f_path in vector_store_dir.glob("*"):
            if f_path.is_file():
                f_path.unlink(missing_ok=True)
    set_global_faiss_vector_store(None)
    set_global_vector_index(None)
    logger.info("Llama_ops: VECTOR_STORE_PATH cleared and global instances reset.")


def get_faiss_index_type_description(faiss_store: Optional[CustomFaissVectorStore]) -> str:
    if not faiss_store or not faiss_store._faiss_index:
        return "FAISS store not available."
    f_index = faiss_store._faiss_index
    if isinstance(f_index, faiss.IndexIDMap2):
        return "IndexIDMap2 (supports remove_ids)"
    return f"Other FAISS type ({type(f_index).__name__})"