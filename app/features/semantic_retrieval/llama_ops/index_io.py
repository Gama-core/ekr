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

logger = logging.getLogger(__name__)


def ensure_faiss_vector_store_with_idmap(recreate: bool = False) -> FaissVectorStore:
    global_faiss_store = get_global_faiss_vector_store()
    initialize_llama_index_settings()

    faiss_index_path_obj = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
    embedding_dim = core_settings.ACTIVE_EMBEDDING_DIMENSION

    if global_faiss_store and not recreate:
        if not isinstance(global_faiss_store._faiss_index, faiss.IndexIDMap):
            logger.warning(
                f"Llama_ops: Global FAISS store is not IndexIDMap (type: {type(global_faiss_store._faiss_index)}). Forcing recreation with IndexIDMap.")
            recreate = True
        elif global_faiss_store._faiss_index.d != embedding_dim:  # d is dimension for IndexIDMap's underlying index
            actual_dim = global_faiss_store._faiss_index.index.d if hasattr(global_faiss_store._faiss_index,
                                                                            'index') else global_faiss_store._faiss_index.d
            if actual_dim != embedding_dim:
                logger.warning(f"Llama_ops: Global FAISS store dimension ({actual_dim}) "
                               f"differs from config ({embedding_dim}). Forcing recreation.")
                recreate = True
        else:
            return global_faiss_store

    if recreate:
        logger.info("Llama_ops: Recreating FAISS vector store with IndexIDMap.")
        set_global_faiss_vector_store(None)  # Clear global to force re-creation path below

    faiss_idmap_index: Optional[faiss.IndexIDMap] = None

    if faiss_index_path_obj.exists() and not recreate:
        logger.info(f"Llama_ops: Loading FAISS IndexIDMap from: {faiss_index_path_obj}")
        try:
            loaded_raw_faiss_index = faiss.read_index(str(faiss_index_path_obj))
            if not isinstance(loaded_raw_faiss_index, faiss.IndexIDMap):
                logger.warning(
                    f"Llama_ops: Loaded FAISS index from {faiss_index_path_obj} is {type(loaded_raw_faiss_index)}, not IndexIDMap. "
                    "Recreating as IndexIDMap wrapping IndexFlatL2 for robust ID management and deletion."
                )
                clear_index_storage_completely()  # Clear old incompatible files
                flat_index = faiss.IndexFlatL2(embedding_dim)
                faiss_idmap_index = faiss.IndexIDMap(flat_index)
            else:
                # Check dimension of the sub-index
                current_dim = loaded_raw_faiss_index.index.d if hasattr(loaded_raw_faiss_index,
                                                                        'index') else loaded_raw_faiss_index.d
                if current_dim != embedding_dim:
                    logger.error(
                        f"Llama_ops: FAISS IndexIDMap's sub-index dimension mismatch! Disk: {current_dim}, Config: {embedding_dim}. Recreating.")
                    clear_index_storage_completely()
                    flat_index = faiss.IndexFlatL2(embedding_dim)
                    faiss_idmap_index = faiss.IndexIDMap(flat_index)
                else:
                    faiss_idmap_index = loaded_raw_faiss_index
                    logger.info(
                        f"Llama_ops: FAISS IndexIDMap (sub-index type: {type(faiss_idmap_index.index)}) loaded with {faiss_idmap_index.ntotal} vectors.")
        except Exception as e:
            logger.warning(
                f"Llama_ops: Failed to load or validate FAISS IndexIDMap from {faiss_index_path_obj} (Error: {e}). Creating new one.")
            flat_index = faiss.IndexFlatL2(embedding_dim)
            faiss_idmap_index = faiss.IndexIDMap(flat_index)
    else:
        logger.info(f"Llama_ops: Creating new FAISS IndexFlatL2 wrapped in IndexIDMap (dim: {embedding_dim}).")
        flat_index = faiss.IndexFlatL2(embedding_dim)
        faiss_idmap_index = faiss.IndexIDMap(flat_index)

    new_faiss_store = FaissVectorStore(faiss_index=faiss_idmap_index)
    set_global_faiss_vector_store(new_faiss_store)
    return new_faiss_store


def ensure_vector_index(recreate_faiss: bool = False) -> VectorStoreIndex:
    global_vector_index = get_global_vector_index()
    initialize_llama_index_settings()

    if recreate_faiss and global_vector_index:
        logger.info("Llama_ops: Recreating FAISS store, will also re-initialize LlamaIndex VectorStoreIndex.")
        set_global_vector_index(None)

    current_vector_index = get_global_vector_index()  # Re-fetch
    if current_vector_index and not recreate_faiss:
        if current_vector_index.vector_store is not get_global_faiss_vector_store():
            logger.warning("Llama_ops: Mismatch VectorStoreIndex's vector_store and global. Re-linking.")
            current_vector_index._vector_store = get_global_faiss_vector_store()  # type: ignore
        return current_vector_index

    vector_store = ensure_faiss_vector_store_with_idmap(recreate=recreate_faiss)
    if not vector_store:
        raise RuntimeError("Llama_ops: Failed to initialize FaissVectorStore with IndexIDMap.")

    storage_context_path = core_settings.VECTOR_STORE_PATH
    docstore_path = storage_context_path / "docstore.json"
    index_store_path = storage_context_path / "index_store.json"
    new_index: Optional[VectorStoreIndex] = None

    try:
        if recreate_faiss or not docstore_path.exists() or not index_store_path.exists():
            logger.info(
                "Llama_ops: Initializing new LlamaIndex VectorStoreIndex structure (FAISS recreated or metadata missing).")
            if recreate_faiss:  # Clear LlamaIndex JSONs if FAISS was fully remade
                for f_meta in core_settings.VECTOR_STORE_PATH.glob("*.json"): f_meta.unlink(missing_ok=True)

            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                docstore=SimpleDocumentStore(),
                index_store=SimpleIndexStore()
            )
            new_index = VectorStoreIndex.from_documents(
                [], storage_context=storage_context, embed_model=LlamaSettings.embed_model
            )
            logger.info("Llama_ops: Initialized new empty VectorStoreIndex with IndexIDMap.")
            persist_index_and_vector_store(new_index, vector_store)
        else:
            logger.info(f"Llama_ops: Loading VectorStoreIndex from LlamaIndex storage: {storage_context_path}...")
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store, persist_dir=str(storage_context_path)
            )
            new_index = load_index_from_storage(
                storage_context, embed_model=LlamaSettings.embed_model
            )
            new_index._vector_store = vector_store  # type: ignore
            faiss_total = vector_store._faiss_index.ntotal if vector_store._faiss_index else 'N/A'
            logger.info(
                f"Llama_ops: Successfully loaded VectorStoreIndex. FAISS (IndexIDMap) has {faiss_total} vectors.")
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
            f"Llama_ops: FAISS IndexIDMap persisted to {faiss_path} with {vector_store_to_persist._faiss_index.ntotal} vectors.")
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
    if isinstance(f_index, faiss.IndexIDMap):
        underlying_index = f_index.index
        return f"IndexIDMap(sub_index: {type(underlying_index).__name__}, supports remove_ids)"
    elif isinstance(f_index, faiss.IndexFlatL2):
        return "IndexFlatL2 (physical vector deletion via full rebuild, no ID mapping)"
    else:
        return f"Other ({type(f_index).__name__})"