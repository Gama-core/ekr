# app/features/semantic_retrieval/llama_ops/index_io.py
import logging
from typing import Optional, cast

import faiss
import numpy as np
from pathlib import Path

from llama_index.core import (
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings as LlamaSettings,
)
# from llama_index.vector_stores.faiss import FaissVectorStore # Using custom one
from .custom_faiss_vstore import CustomFaissVectorStore, MAPPINGS_FILENAME

from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

from app.core.config import settings as core_settings
from app.features.semantic_retrieval.llama_ops import (
    get_global_faiss_vector_store, set_global_faiss_vector_store,
    get_global_vector_index, set_global_vector_index,
    initialize_llama_index_settings
)

logger = logging.getLogger(__name__)


def ensure_faiss_vector_store_with_idmap(recreate: bool = False) -> CustomFaissVectorStore:
    global_faiss_store_obj = get_global_faiss_vector_store()  # This is Optional[CustomFaissVectorStore]
    initialize_llama_index_settings()

    faiss_index_physical_path = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
    embedding_dim = core_settings.ACTIVE_EMBEDDING_DIMENSION
    vector_store_persist_path_str = str(core_settings.VECTOR_STORE_PATH.resolve())

    if global_faiss_store_obj and isinstance(global_faiss_store_obj, CustomFaissVectorStore) and not recreate:
        # Basic checks on the existing global instance
        if not global_faiss_store_obj._faiss_index:  # type: ignore
            logger.warning("Llama_ops: Global CustomFaissVectorStore has no _faiss_index. Recreating.")
            recreate = True
        elif not isinstance(global_faiss_store_obj._faiss_index, faiss.IndexIDMap2):  # type: ignore
            logger.warning(
                f"Llama_ops: Global FAISS store (Custom) _faiss_index is not IndexIDMap2 (type: {type(global_faiss_store_obj._faiss_index)}). Forcing recreation.")  # type: ignore
            recreate = True
        elif hasattr(global_faiss_store_obj._faiss_index,
                     'index') and global_faiss_store_obj._faiss_index.index.d != embedding_dim:  # type: ignore
            actual_dim = global_faiss_store_obj._faiss_index.index.d  # type: ignore
            logger.warning(
                f"Llama_ops: Global FAISS store (Custom with IndexIDMap2) sub-index dimension ({actual_dim}) "
                f"differs from config ({embedding_dim}). Forcing recreation.")
            recreate = True

        if not recreate:
            logger.debug(
                f"Llama_ops: Using existing global CustomFaissVectorStore. Next FAISS ID: {global_faiss_store_obj._next_faiss_id}")  # type: ignore
            return global_faiss_store_obj

    # --- Creation or Recreation Path ---
    if recreate:
        logger.info("Llama_ops: Recreating FAISS vector store with IndexIDMap2 using CustomFaissVectorStore.")
        mapping_file_to_clear = core_settings.VECTOR_STORE_PATH / MAPPINGS_FILENAME
        if mapping_file_to_clear.exists():
            try:
                mapping_file_to_clear.unlink()
                logger.info(f"Llama_ops: Cleared old mappings file: {mapping_file_to_clear}")
            except Exception as e_unlink:
                logger.warning(f"Llama_ops: Could not delete old mappings file {mapping_file_to_clear}: {e_unlink}")
        set_global_faiss_vector_store(None)  # Clear global instance before creating new

    faiss_idmap2_index: faiss.IndexIDMap2  # Type hint for clarity

    if faiss_index_physical_path.exists() and not recreate:
        logger.info(
            f"Llama_ops: Loading FAISS IndexIDMap2 for CustomFaissVectorStore from: {faiss_index_physical_path}")
        try:
            loaded_raw_faiss_index = faiss.read_index(str(faiss_index_physical_path))
            if not isinstance(loaded_raw_faiss_index, faiss.IndexIDMap2):
                logger.warning(
                    f"Llama_ops: Loaded FAISS index from {faiss_index_physical_path} is {type(loaded_raw_faiss_index)}, not IndexIDMap2. Recreating.")
                flat_index = faiss.IndexFlatL2(embedding_dim)
                faiss_idmap2_index = faiss.IndexIDMap2(flat_index)
            elif hasattr(loaded_raw_faiss_index, 'index') and loaded_raw_faiss_index.index.d != embedding_dim:
                logger.error(
                    f"Llama_ops: FAISS IndexIDMap2's sub-index dimension mismatch! Disk: {loaded_raw_faiss_index.index.d}, Config: {embedding_dim}. Recreating.")
                flat_index = faiss.IndexFlatL2(embedding_dim)
                faiss_idmap2_index = faiss.IndexIDMap2(flat_index)
            else:
                faiss_idmap2_index = cast(faiss.IndexIDMap2, loaded_raw_faiss_index)
                sub_index_type = type(faiss_idmap2_index.index).__name__ if hasattr(faiss_idmap2_index,
                                                                                    'index') else 'N/A'
                logger.info(
                    f"Llama_ops: FAISS IndexIDMap2 (sub-index type: {sub_index_type}) loaded with {faiss_idmap2_index.ntotal} vectors.")
        except Exception as e:
            logger.warning(
                f"Llama_ops: Failed to load or validate FAISS IndexIDMap2 from {faiss_index_physical_path} (Error: {e}). Creating new one.")
            flat_index = faiss.IndexFlatL2(embedding_dim)
            faiss_idmap2_index = faiss.IndexIDMap2(flat_index)
    else:  # Create new if no file or if recreating
        logger.info(
            f"Llama_ops: Creating new FAISS IndexFlatL2 wrapped in IndexIDMap2 for CustomFaissVS (dim: {embedding_dim}).")
        flat_index = faiss.IndexFlatL2(embedding_dim)
        faiss_idmap2_index = faiss.IndexIDMap2(flat_index)

    new_custom_faiss_store = CustomFaissVectorStore(
        faiss_index=faiss_idmap2_index,
        persist_path=vector_store_persist_path_str  # Pass the directory path
    )
    # _load_mappings() is called in __init__ of CustomFaissVectorStore if persist_path is provided

    set_global_faiss_vector_store(new_custom_faiss_store)
    logger.info(
        f"Llama_ops: CustomFaissVectorStore initialized/loaded. Next internal FAISS ID: {new_custom_faiss_store._next_faiss_id}")  # type: ignore
    return new_custom_faiss_store


def ensure_vector_index(recreate_faiss: bool = False) -> VectorStoreIndex:
    global_vector_index = get_global_vector_index()
    initialize_llama_index_settings()  # Ensures LlamaSettings are populated

    if recreate_faiss and global_vector_index:
        logger.info("Llama_ops: Recreating FAISS store, will also re-initialize LlamaIndex VectorStoreIndex.")
        set_global_vector_index(None)
        # When FAISS is recreated, LlamaIndex metadata should also be considered for clearing
        # clear_index_storage_completely() handles this robustly by deleting all files.
        # If only recreating FAISS but not LlamaIndex JSONs, ensure they are compatible.
        # The safest is to clear all if faiss is recreated from scratch.
        if recreate_faiss:  # Explicitly clear all storage if faiss is being fully remade
            clear_index_storage_completely()

    current_vector_index = get_global_vector_index()
    if current_vector_index and not recreate_faiss:  # Added space for readability
        if current_vector_index.vector_store is not get_global_faiss_vector_store():
            logger.warning("Llama_ops: Mismatch VectorStoreIndex's vector_store and global. Re-linking.")
            current_vector_index._vector_store = get_global_faiss_vector_store()  # type: ignore
        logger.debug("Llama_ops: Returning existing global VectorStoreIndex.")
        return current_vector_index

    # If we reach here, we need to create or load the VectorStoreIndex
    # ensure_faiss_vector_store_with_idmap handles its own `recreate` logic for the FAISS part
    # The `recreate_faiss` passed to `ensure_vector_index` primarily controls LlamaIndex metadata recreation.
    vector_store = ensure_faiss_vector_store_with_idmap(recreate=recreate_faiss)
    if not vector_store:
        raise RuntimeError("Llama_ops: Failed to initialize CustomFaissVectorStore with IndexIDMap2.")

    storage_context_path = core_settings.VECTOR_STORE_PATH
    docstore_path = storage_context_path / "docstore.json"
    index_store_path = storage_context_path / "index_store.json"
    # graph_store_path = storage_context_path / "graph_store.json" # If you use KnowledgeGraphIndex

    new_index: Optional[VectorStoreIndex] = None

    # If recreate_faiss was true, clear_index_storage_completely() was called, so JSONs are gone.
    # So, the condition simplifies to checking if docstore exists.
    llama_metadata_exists = docstore_path.exists() and index_store_path.exists()

    try:
        if not llama_metadata_exists:  # If LlamaIndex metadata is missing (or was cleared by recreate_faiss)
            logger.info(
                "Llama_ops: Initializing new LlamaIndex VectorStoreIndex structure (LlamaIndex metadata missing or FAISS was recreated).")
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                docstore=SimpleDocumentStore(),
                index_store=SimpleIndexStore(),
                # graph_store=SimpleGraphStore(), # If using KnowledgeGraphIndex
            )
            # When creating from empty documents, it initializes the structure
            new_index = VectorStoreIndex.from_documents(
                [], storage_context=storage_context, embed_model=LlamaSettings.embed_model
            )
            logger.info(
                "Llama_ops: Initialized new empty VectorStoreIndex with CustomFaissVectorStore (IndexIDMap2 based).")
            # Persist immediately to create the .json files for LlamaIndex's structure
            persist_index_and_vector_store(new_index, vector_store)
        else:
            logger.info(f"Llama_ops: Loading VectorStoreIndex from LlamaIndex storage: {storage_context_path}...")
            # StorageContext will load from persist_dir if files exist
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,  # Provide the already configured vector store
                persist_dir=str(storage_context_path),
                docstore=SimpleDocumentStore.from_persist_path(str(docstore_path)),
                index_store=SimpleIndexStore.from_persist_path(str(index_store_path)),
                # graph_store=SimpleGraphStore.from_persist_path(str(graph_store_path)) # If used
            )
            new_index = load_index_from_storage(
                storage_context,
                embed_model=LlamaSettings.embed_model
            )
            # Ensure the loaded index uses our (potentially freshly loaded) vector store instance
            new_index._vector_store = vector_store  # type: ignore

            faiss_total = vector_store._faiss_index.ntotal if vector_store._faiss_index else 'N/A'  # type: ignore
            logger.info(
                f"Llama_ops: Successfully loaded VectorStoreIndex. DocStore has {len(new_index.docstore.docs)} docs. FAISS (IndexIDMap2) has {faiss_total} vectors.")
            logger.info(
                f"Llama_ops: Index_struct nodes_dict contains {len(new_index.index_struct.nodes_dict)} nodes after load.")  # type: ignore
            if new_index.index_struct.nodes_dict:  # type: ignore
                logger.info(
                    f"Llama_ops: First few keys in nodes_dict after load: {list(new_index.index_struct.nodes_dict.keys())[:5]}")  # type: ignore

    except Exception as e:
        logger.error(f"Llama_ops: Error loading/initializing VectorStoreIndex: {e}. Falling back to fresh creation.",
                     exc_info=True)
        # If loading fails, attempt a full recreation by clearing everything
        clear_index_storage_completely()
        return ensure_vector_index(recreate_faiss=True)  # Call with recreate_faiss=True

    set_global_vector_index(new_index)
    return new_index


def persist_index_and_vector_store(index_to_persist: Optional[VectorStoreIndex],
                                   vector_store_to_persist: Optional[CustomFaissVectorStore]):
    if not index_to_persist:
        logger.error("Llama_ops: Cannot persist LlamaIndex: index_to_persist is None.")
        return
    if not vector_store_to_persist or not vector_store_to_persist._faiss_index:  # type: ignore
        logger.error("Llama_ops: Cannot persist FAISS: custom vector_store or its _faiss_index is None.")
        return

    try:
        persist_dir = core_settings.VECTOR_STORE_PATH
        index_to_persist.storage_context.persist(persist_dir=str(persist_dir))
        logger.debug(f"Llama_ops: LlamaIndex storage context (docstore.json, etc.) persisted to {persist_dir}")

        faiss_idx_path = persist_dir / core_settings.FAISS_INDEX_FILENAME_DEFAULT
        faiss.write_index(vector_store_to_persist._faiss_index, str(faiss_idx_path))  # type: ignore
        logger.info(
            f"Llama_ops: FAISS IndexIDMap2 (from CustomFaissVectorStore) persisted to {faiss_idx_path} with {vector_store_to_persist._faiss_index.ntotal} vectors.")  # type: ignore

        # Persist our custom mappings from CustomFaissVectorStore
        vector_store_to_persist._save_mappings()  # It uses its _persist_path which should be persist_dir

    except Exception as e:
        logger.exception(f"Llama_ops: Error during index persistence: {e}")


def clear_index_storage_completely():
    logger.info("Llama_ops: Clearing all files in VECTOR_STORE_PATH for full rebuild...")
    vector_store_dir = core_settings.VECTOR_STORE_PATH
    if vector_store_dir.exists():
        for f_path in vector_store_dir.glob("*"):  # Clears .idx, .json (mappings, docstore, etc.)
            if f_path.is_file():
                try:
                    f_path.unlink(missing_ok=True)
                except Exception as e:
                    logger.warning(f"Llama_ops: Could not delete file {f_path}: {e}")
    else:  # Ensure directory exists even if we cleared it or it never existed
        vector_store_dir.mkdir(parents=True, exist_ok=True)

    set_global_faiss_vector_store(None)
    set_global_vector_index(None)
    logger.info("Llama_ops: VECTOR_STORE_PATH cleared and global instances reset.")


def get_faiss_index_type_description(faiss_store: Optional[CustomFaissVectorStore]) -> str:  # Updated type hint
    if not faiss_store or not faiss_store._faiss_index:  # type: ignore
        return "FAISS store (Custom) not available or not initialized."

    f_index = faiss_store._faiss_index  # type: ignore
    if isinstance(f_index, faiss.IndexIDMap2):
        underlying_index = f_index.index if hasattr(f_index, 'index') else None
        sub_index_name = type(underlying_index).__name__ if underlying_index else "N/A"
        return f"IndexIDMap2(sub_index: {sub_index_name}, supports remove_ids)"
    elif isinstance(f_index, faiss.IndexIDMap):  # Should ideally not be used now
        underlying_index = f_index.index if hasattr(f_index, 'index') else None
        sub_index_name = type(underlying_index).__name__ if underlying_index else "N/A"
        return f"IndexIDMap(sub_index: {sub_index_name}, supports remove_ids)"
    elif isinstance(f_index, faiss.IndexFlatL2):  # Fallback if somehow it's FlatL2
        return "IndexFlatL2 (no ID mapping, deletion by full rebuild)"
    else:
        return f"Other FAISS type ({type(f_index).__name__})"