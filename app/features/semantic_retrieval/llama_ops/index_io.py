# app/features/semantic_retrieval/llama_ops/index_io.py
import logging
from typing import Optional

import faiss
import numpy as np
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings as LlamaSettings,
)
from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

from app.core.config import settings as core_settings
from app.features.semantic_retrieval.llama_ops import (
    get_global_faiss_vector_store, set_global_faiss_vector_store,
    get_global_vector_index, set_global_vector_index,
    initialize_llama_index_settings
)
from .custom_faiss_vstore import CustomFaissVectorStore
logger = logging.getLogger(__name__)


def ensure_faiss_vector_store_with_idmap(
        recreate: bool = False) -> CustomFaissVectorStore:  # Return CustomFaissVectorStore
    global_faiss_store = get_global_faiss_vector_store()
    initialize_llama_index_settings()

    faiss_index_path_obj = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
    embedding_dim = core_settings.ACTIVE_EMBEDDING_DIMENSION

    if global_faiss_store and isinstance(global_faiss_store,
                                         CustomFaissVectorStore) and not recreate:  # Check instance type
        # ... (existing checks for IndexIDMap2 and dimension, adapted for CustomFaissVectorStore if needed)
        if not isinstance(global_faiss_store._faiss_index, faiss.IndexIDMap2):
            logger.warning(
                f"Llama_ops: Global FAISS store (Custom) is not IndexIDMap2 (type: {type(global_faiss_store._faiss_index)}). Forcing recreation.")
            recreate = True
        # ... (dimension checks)
        else:
            return cast(CustomFaissVectorStore, global_faiss_store)

    if recreate:
        logger.info("Llama_ops: Recreating FAISS vector store with IndexIDMap2 using CustomFaissVectorStore.")
        set_global_faiss_vector_store(None)

    faiss_idmap2_index: Optional[faiss.IndexIDMap2] = None  # This will be the faiss.Index for the custom store

    # ... (Logic for loading or creating faiss_idmap2_index as IndexIDMap2(IndexFlatL2(embedding_dim)) remains the same) ...
    # Make sure this part correctly creates/loads an faiss.IndexIDMap2 object
    if faiss_index_path_obj.exists() and not recreate:
        logger.info(f"Llama_ops: Loading FAISS IndexIDMap2 for CustomFaissVectorStore from: {faiss_index_path_obj}")
        try:
            loaded_raw_faiss_index = faiss.read_index(str(faiss_index_path_obj))
            if not isinstance(loaded_raw_faiss_index, faiss.IndexIDMap2):
                logger.warning(
                    f"Llama_ops: Loaded FAISS index is {type(loaded_raw_faiss_index)}, not IndexIDMap2. Recreating."
                )
                clear_index_storage_completely()
                flat_index = faiss.IndexFlatL2(embedding_dim)
                faiss_idmap2_index = faiss.IndexIDMap2(flat_index)
            # ... (dimension check for loaded_raw_faiss_index.index.d)
            else:
                faiss_idmap2_index = loaded_raw_faiss_index  # type: ignore
        except Exception as e:
            # ... (error handling, create new faiss_idmap2_index)
            logger.warning(f"Llama_ops: Failed to load FAISS IndexIDMap2 (Error: {e}). Creating new one.")
            flat_index = faiss.IndexFlatL2(embedding_dim)
            faiss_idmap2_index = faiss.IndexIDMap2(flat_index)

    else:  # Create new
        logger.info(
            f"Llama_ops: Creating new FAISS IndexFlatL2 wrapped in IndexIDMap2 for CustomFaissVectorStore (dim: {embedding_dim}).")
        flat_index = faiss.IndexFlatL2(embedding_dim)
        faiss_idmap2_index = faiss.IndexIDMap2(flat_index)

    # Instantiate the CUSTOM vector store
    new_faiss_store = CustomFaissVectorStore(faiss_index=faiss_idmap2_index)
    set_global_faiss_vector_store(new_faiss_store)
    return new_faiss_store


# ensure_vector_index will now receive CustomFaissVectorStore from ensure_faiss_vector_store_with_idmap
# Its type hints for vector_store might need adjustment if you were very specific.
# The rest of index_io.py (ensure_vector_index, persist_index_and_vector_store, etc.)
# should largely work, but their logging messages related to "FaissVectorStore"
# might now be referring to "CustomFaissVectorStore".

# --- The rest of ensure_vector_index, persist_index_and_vector_store, clear_index_storage_completely
# --- should be updated to reflect IndexIDMap2 in their logging if they specifically mention the type.

def ensure_vector_index(recreate_faiss: bool = False) -> VectorStoreIndex:
    # (Ensure logging here mentions IndexIDMap2 if it logs the type)
    # ... (logic mostly same, ensure it uses ensure_faiss_vector_store_with_idmap)
    global_vector_index = get_global_vector_index()
    initialize_llama_index_settings()

    if recreate_faiss and global_vector_index:
        logger.info("Llama_ops: Recreating FAISS store, will also re-initialize LlamaIndex VectorStoreIndex.")
        set_global_vector_index(None)

    current_vector_index = get_global_vector_index()
    if current_vector_index and not recreate_faiss:
        if current_vector_index.vector_store is not get_global_faiss_vector_store(): # type: ignore
            logger.warning("Llama_ops: Mismatch VectorStoreIndex's vector_store and global. Re-linking.")
            current_vector_index._vector_store = get_global_faiss_vector_store() # type: ignore
        return current_vector_index

    vector_store = ensure_faiss_vector_store_with_idmap(recreate=recreate_faiss)
    if not vector_store:
        raise RuntimeError("Llama_ops: Failed to initialize FaissVectorStore with IndexIDMap2.")

    storage_context_path = core_settings.VECTOR_STORE_PATH
    docstore_path = storage_context_path / "docstore.json"
    index_store_path = storage_context_path / "index_store.json"
    new_index: Optional[VectorStoreIndex] = None

    try:
        if recreate_faiss or not docstore_path.exists() or not index_store_path.exists():
            logger.info(
                "Llama_ops: Initializing new LlamaIndex VectorStoreIndex structure (FAISS recreated or metadata missing).")
            if recreate_faiss:
                for f_meta in core_settings.VECTOR_STORE_PATH.glob("*.json"): f_meta.unlink(missing_ok=True)

            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                docstore=SimpleDocumentStore(),
                index_store=SimpleIndexStore()
            )
            new_index = VectorStoreIndex.from_documents(
                [], storage_context=storage_context, embed_model=LlamaSettings.embed_model
            )
            logger.info("Llama_ops: Initialized new empty VectorStoreIndex with IndexIDMap2 based FAISS store.")
            persist_index_and_vector_store(new_index, vector_store)
        else:
            logger.info(f"Llama_ops: Loading VectorStoreIndex from LlamaIndex storage: {storage_context_path}...")
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store, persist_dir=str(storage_context_path)
            )
            new_index = load_index_from_storage(
                storage_context, embed_model=LlamaSettings.embed_model
            )
            new_index._vector_store = vector_store # type: ignore
            faiss_total = vector_store._faiss_index.ntotal if vector_store._faiss_index else 'N/A'
            logger.info(
                f"Llama_ops: Successfully loaded VectorStoreIndex. FAISS (IndexIDMap2) has {faiss_total} vectors.")
    except Exception as e:
        logger.error(f"Llama_ops: Error loading/initializing VectorStoreIndex: {e}. Fallback to fresh.", exc_info=True)
        return ensure_vector_index(recreate_faiss=True)

    set_global_vector_index(new_index)
    return new_index


def persist_index_and_vector_store(index_to_persist: Optional[VectorStoreIndex],
                                   vector_store_to_persist: Optional[FaissVectorStore]):
    if not index_to_persist: logger.error("Llama_ops: Cannot persist LlamaIndex: index_to_persist is None."); return
    if not vector_store_to_persist or not vector_store_to_persist._faiss_index:
        logger.error("Llama_ops: Cannot persist FAISS: vector_store or its _faiss_index is None.");
        return

    try:
        index_to_persist.storage_context.persist(persist_dir=str(core_settings.VECTOR_STORE_PATH))
        logger.debug(f"Llama_ops: LlamaIndex storage context persisted to {core_settings.VECTOR_STORE_PATH}")

        faiss_path = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
        faiss.write_index(vector_store_to_persist._faiss_index, str(faiss_path))
        logger.info(
            f"Llama_ops: FAISS IndexIDMap2 persisted to {faiss_path} with {vector_store_to_persist._faiss_index.ntotal} vectors.") # Updated log
    except Exception as e:
        logger.exception(f"Llama_ops: Error during index persistence: {e}")


def clear_index_storage_completely():
    logger.info("Llama_ops: Clearing all files in VECTOR_STORE_PATH for full rebuild...")
    if core_settings.VECTOR_STORE_PATH.exists():
        for f_path in core_settings.VECTOR_STORE_PATH.glob("*"):
            if f_path.is_file():
                try:
                    f_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Llama_ops: Could not delete file {f_path}: {e}")
    set_global_faiss_vector_store(None)
    set_global_vector_index(None)


def get_faiss_index_type_description(faiss_store: Optional[FaissVectorStore]) -> str:
    if not faiss_store or not faiss_store._faiss_index:
        return "FAISS store not available or not initialized."

    f_index = faiss_store._faiss_index
    if isinstance(f_index, faiss.IndexIDMap2): # Primary check for IndexIDMap2
        underlying_index = f_index.index if hasattr(f_index, 'index') else None
        sub_index_name = type(underlying_index).__name__ if underlying_index else "N/A"
        return f"IndexIDMap2(sub_index: {sub_index_name}, supports remove_ids)"
    elif isinstance(f_index, faiss.IndexFlatL2):
        return "IndexFlatL2 (physical vector deletion via full rebuild, no ID mapping)"
    elif isinstance(f_index, faiss.IndexIDMap): # Fallback for old IndexIDMap if ever encountered
        underlying_index = f_index.index if hasattr(f_index, 'index') else None
        sub_index_name = type(underlying_index).__name__ if underlying_index else "N/A"
        return f"IndexIDMap(sub_index: {sub_index_name}, supports remove_ids)"
    else:
        return f"Other ({type(f_index).__name__})"