# app/features/semantic_retrieval/index_service.py
import logging
from pathlib import Path
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from llama_index.core import (
    Document as LlamaDocument,
    Settings as LlamaSettings,
    VectorStoreIndex,
    StorageContext,
    load_index_from_storage,
)
from llama_index.llms.openai import OpenAI as LlamaOpenAI
from llama_index.embeddings.huggingface import HuggingFaceEmbedding

from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

import faiss  # Ensure faiss is imported

from app.core.config import settings as core_settings
from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema
from app.db_connectors.note_reader_service import get_all_notes_for_indexing_stream, \
    get_notes_by_user_for_indexing_stream
from app.features.semantic_retrieval.config import semantic_retrieval_config

logger = logging.getLogger(__name__)

_vector_index: Optional[VectorStoreIndex] = None
_faiss_vector_store: Optional[FaissVectorStore] = None
_llama_settings_initialized: bool = False


def _initialize_llama_index_core_settings():
    """Initializes global LlamaIndex settings (LLM, embed_model, chunk_size)."""
    global _llama_settings_initialized
    if _llama_settings_initialized and LlamaSettings.llm and LlamaSettings.embed_model:
        # logger.debug("LlamaIndex Core Settings already configured.")
        return

    logger.info("Configuring LlamaIndex global settings for semantic retrieval feature...")
    try:
        LlamaSettings.llm = LlamaOpenAI(  # Qwen Chat LLM for LlamaIndex internal tasks
            model=core_settings.QWEN_DEFAULT_MODEL,
            api_base=core_settings.QWEN_BASE_URL,
            api_key=core_settings.QWEN_API_KEY,
            temperature=0.1,
        )
        logger.info(f"LlamaIndex LLM configured with Qwen model: {core_settings.QWEN_DEFAULT_MODEL}")

        if core_settings.EMBEDDING_MODEL_PROVIDER == "huggingface":
            LlamaSettings.embed_model = HuggingFaceEmbedding(
                model_name=core_settings.HF_EMBEDDING_MODEL_NAME
            )
            logger.info(
                f"LlamaIndex Embed Model configured with HuggingFace: {core_settings.HF_EMBEDDING_MODEL_NAME} "
                f"(Expected Dim: {core_settings.ACTIVE_EMBEDDING_DIMENSION})"
            )
        # Add elif for "dashscope" or other providers if you re-enable them
        else:
            err_msg = f"Unsupported EMBEDDING_MODEL_PROVIDER: '{core_settings.EMBEDDING_MODEL_PROVIDER}'"
            logger.error(err_msg)
            raise ValueError(err_msg)

        LlamaSettings.chunk_size = semantic_retrieval_config.DEFAULT_CHUNK_SIZE
        LlamaSettings.chunk_overlap = semantic_retrieval_config.DEFAULT_CHUNK_OVERLAP
        logger.info(
            f"LlamaIndex chunk_size: {LlamaSettings.chunk_size}, chunk_overlap: {LlamaSettings.chunk_overlap}")
        _llama_settings_initialized = True
    except Exception as e:
        logger.exception(f"CRITICAL: Failed to initialize LlamaIndex Core Settings: {e}")
        raise  # This is critical for the app to function


def _db_note_to_llama_doc(note_data: DBNoteForIndexSchema) -> LlamaDocument:
    """Converts a database note schema to a LlamaIndex Document."""
    doc_id = f"note_{note_data.id}"  # Consistent Doc ID
    metadata = {
        "note_id": str(note_data.id),
        "title": str(note_data.title or "Untitled"),
        "creation_date": str(note_data.creation_date.isoformat() if note_data.creation_date else ""),
        "owner_id": str(note_data.owner_id),  # For user-specific filtering
        "source_type": "note"
    }
    # Ensure text_content is not empty for FAISS, but also not just whitespace if possible
    text_content = note_data.text_content if note_data.text_content and note_data.text_content.strip() else " "  # FAISS requires non-empty
    return LlamaDocument(text=text_content, doc_id=doc_id, metadata=metadata)


def get_faiss_vector_store(recreate: bool = False) -> FaissVectorStore:
    """Gets or creates a FaissVectorStore, ensuring it uses IndexFlatL2."""
    global _faiss_vector_store
    _initialize_llama_index_core_settings()  # Crucial: embed_model must be set to get ACTIVE_EMBEDDING_DIMENSION

    faiss_index_path_obj = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
    embedding_dim = core_settings.ACTIVE_EMBEDDING_DIMENSION

    if _faiss_vector_store and not recreate:
        # If the existing global store is not IndexFlatL2 (e.g. old IndexIDMap), force recreation
        if not isinstance(_faiss_vector_store._faiss_index, faiss.IndexFlatL2) \
                and not isinstance(_faiss_vector_store._faiss_index, faiss.IndexFlatIP):  # Allow IP if we switched
            logger.warning(
                f"Global _faiss_vector_store is not IndexFlatL2/IP (type: {type(_faiss_vector_store._faiss_index)}). Forcing recreation.")
            recreate = True
        elif _faiss_vector_store._faiss_index.d != embedding_dim:
            logger.warning(f"Global _faiss_vector_store dimension ({_faiss_vector_store._faiss_index.d}) "
                           f"differs from config ({embedding_dim}). Forcing recreation.")
            recreate = True
        else:
            # logger.debug("Returning existing _faiss_vector_store (IndexFlatL2/IP, matching dim).")
            return _faiss_vector_store

    # If recreate is true, clear the global singleton to ensure it's remade
    if recreate and _faiss_vector_store:
        logger.info("Recreating FAISS vector store as IndexFlatL2.")
        _faiss_vector_store = None  # Clear it

    if faiss_index_path_obj.exists() and not recreate:
        logger.info(f"Loading FAISS index (expecting IndexFlatL2 compatible) from: {faiss_index_path_obj}")
        try:
            loaded_faiss_index = faiss.read_index(str(faiss_index_path_obj))
            # We strongly prefer IndexFlatL2 for this known-good path.
            # If it's an IDMap, it might cause issues with current LlamaIndex add methods.
            if isinstance(loaded_faiss_index, faiss.IndexIDMap):
                logger.warning(f"Loaded FAISS index from {faiss_index_path_obj} is an IndexIDMap. "
                               "This can cause 'add_with_ids' errors with some LlamaIndex versions. "
                               "Recreating as IndexFlatL2 for stability.")
                faiss_index_path_obj.unlink(missing_ok=True)
                for f_meta in core_settings.VECTOR_STORE_PATH.glob("*.json"): f_meta.unlink(missing_ok=True)
                faiss_index_instance = faiss.IndexFlatL2(embedding_dim)
            elif loaded_faiss_index.d != embedding_dim:
                logger.error(
                    f"FAISS index dimension mismatch! Disk: {loaded_faiss_index.d}, Config: {embedding_dim}. Recreating as IndexFlatL2.")
                faiss_index_path_obj.unlink(missing_ok=True)
                for f_meta in core_settings.VECTOR_STORE_PATH.glob("*.json"): f_meta.unlink(missing_ok=True)
                faiss_index_instance = faiss.IndexFlatL2(embedding_dim)
            else:  # Dimensions match and it's not an IDMap (so, likely FlatL2 or FlatIP)
                faiss_index_instance = loaded_faiss_index
                logger.info(
                    f"FAISS index (type: {type(faiss_index_instance)}) loaded with {faiss_index_instance.ntotal} vectors.")
        except Exception as e:
            logger.warning(
                f"Failed to load FAISS index from {faiss_index_path_obj} (Error: {e}). Creating new IndexFlatL2.")
            faiss_index_instance = faiss.IndexFlatL2(embedding_dim)
    else:  # Recreate or file not found
        logger.info(f"Creating new FAISS IndexFlatL2 (dim: {embedding_dim}).")
        faiss_index_instance = faiss.IndexFlatL2(embedding_dim)  # Defaulting to IndexFlatL2

    _faiss_vector_store = FaissVectorStore(faiss_index=faiss_index_instance)
    return _faiss_vector_store


def get_vector_index(recreate_faiss: bool = False) -> Optional[VectorStoreIndex]:
    """Gets or creates the LlamaIndex VectorStoreIndex, ensuring use of IndexFlatL2."""
    global _vector_index, _faiss_vector_store
    _initialize_llama_index_core_settings()

    # If recreate_faiss is true, also force _vector_index to be None so it's re-established
    if recreate_faiss and _vector_index:
        logger.info("Recreating FAISS store, will also re-initialize LlamaIndex VectorStoreIndex.")
        _vector_index = None

    if _vector_index and not recreate_faiss:  # Check _vector_index first now
        # Ensure the VectorStoreIndex is using the correct global _faiss_vector_store instance
        # This can happen if _faiss_vector_store was recreated but _vector_index wasn't.
        current_vs_instance_in_index = _vector_index.vector_store
        if current_vs_instance_in_index is not _faiss_vector_store:
            logger.warning(
                "Mismatch between VectorStoreIndex's vector_store and global _faiss_vector_store. Re-linking.")
            _vector_index._vector_store = _faiss_vector_store  # type: ignore
        # logger.debug("Returning existing _vector_index.")
        return _vector_index

    # This will get/create _faiss_vector_store (as IndexFlatL2)
    vector_store = get_faiss_vector_store(recreate=recreate_faiss)
    if not _faiss_vector_store:  # Should be set by the call above
        logger.error("Failed to get/create _faiss_vector_store. Cannot initialize VectorStoreIndex.")
        return None

    storage_context_path = core_settings.VECTOR_STORE_PATH
    docstore_path = storage_context_path / "docstore.json"
    index_store_path = storage_context_path / "index_store.json"

    try:
        # If recreating FAISS, or LlamaIndex metadata is missing, start LlamaIndex structure fresh
        if recreate_faiss or not docstore_path.exists() or not index_store_path.exists():
            if recreate_faiss:
                logger.info("FAISS store recreated. Initializing new LlamaIndex VectorStoreIndex structure.")
            else:
                logger.info(
                    "LlamaIndex metadata (docstore.json/index_store.json) not found. Initializing new structure.")

            # Clean up any old LlamaIndex JSON files if we are starting fresh for LlamaIndex part
            if recreate_faiss:  # Only if FAISS itself was remade, ensure JSONs are also fresh
                for f_meta in core_settings.VECTOR_STORE_PATH.glob("*.json"): f_meta.unlink(missing_ok=True)

            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,
                docstore=SimpleDocumentStore(),  # Fresh docstore
                index_store=SimpleIndexStore()  # Fresh index_store
            )
            _vector_index = VectorStoreIndex.from_documents(
                [],  # Initialize empty
                storage_context=storage_context,
                embed_model=LlamaSettings.embed_model  # Crucial: pass the embed_model
            )
            logger.info("Initialized new empty VectorStoreIndex structure with IndexFlatL2.")
            persist_index(_vector_index, vector_store)  # Persist this new empty structure
        else:  # Load existing LlamaIndex metadata
            logger.info(f"Loading VectorStoreIndex from LlamaIndex storage: {storage_context_path}...")
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store,  # Provide the already configured FAISS store
                persist_dir=str(storage_context_path)
            )
            _vector_index = load_index_from_storage(
                storage_context,
                embed_model=LlamaSettings.embed_model  # Crucial: pass the embed_model
            )
            # Ensure the loaded index uses our managed FaissVectorStore instance
            _vector_index._vector_store = vector_store  # type: ignore
            logger.info(
                f"Successfully loaded VectorStoreIndex. FAISS has {vector_store._faiss_index.ntotal if vector_store._faiss_index else 'N/A'} vectors.")

    except Exception as e:
        logger.error(
            f"Error loading or initializing VectorStoreIndex: {e}. Attempting fallback to new empty structure.",
            exc_info=True)
        # Recursive call to try and recover with a completely fresh start
        return get_vector_index(recreate_faiss=True)

    return _vector_index


def persist_index(index_to_persist: Optional[VectorStoreIndex] = None,
                  vector_store_to_persist: Optional[FaissVectorStore] = None):
    """Persists the LlamaIndex storage context and the FAISS index file."""
    idx = index_to_persist if index_to_persist is not None else _vector_index
    vs = vector_store_to_persist if vector_store_to_persist is not None else _faiss_vector_store

    if not idx: logger.error("Cannot persist LlamaIndex: _vector_index is None."); return
    if not vs: logger.error("Cannot persist FAISS: _faiss_vector_store is None."); return
    if not vs._faiss_index: logger.error("Cannot persist FAISS: _faiss_vector_store._faiss_index is None."); return

    try:
        # Persist LlamaIndex's own metadata (docstore, index_store etc.)
        idx.storage_context.persist(persist_dir=str(core_settings.VECTOR_STORE_PATH))
        logger.debug(f"LlamaIndex storage context persisted to {core_settings.VECTOR_STORE_PATH}")

        # Persist the FAISS index data separately
        faiss_path = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
        faiss.write_index(vs._faiss_index, str(faiss_path))
        logger.info(f"FAISS index (IndexFlatL2) persisted to {faiss_path} with {vs._faiss_index.ntotal} vectors.")
    except Exception as e:
        logger.exception(f"Error during index persistence: {e}")


async def build_full_index(db: Session, force_rebuild: bool = False) -> Tuple[int, int]:
    """Builds the full index from all database notes, using IndexFlatL2."""
    global _vector_index, _faiss_vector_store
    logger.info(f"Full index build started. Force rebuild: {force_rebuild}")

    if force_rebuild:
        logger.info("Forcing rebuild: clearing all files in VECTOR_STORE_PATH...")
        # More robust clearing:
        if core_settings.VECTOR_STORE_PATH.exists():
            for f_path in core_settings.VECTOR_STORE_PATH.glob("*"):  # Clear all files and subdirs if any
                if f_path.is_file(): f_path.unlink(missing_ok=True)
                # Add rmtree for subdirs if necessary, but usually it's flat files.
        _faiss_vector_store = None  # Ensure it's None so get_faiss_vector_store recreates
        _vector_index = None  # Ensure it's None so get_vector_index recreates

    # This will setup IndexFlatL2 and a compatible LlamaIndex structure
    index = get_vector_index(recreate_faiss=force_rebuild)
    vector_store = _faiss_vector_store  # This global is updated by get_faiss_vector_store / get_vector_index

    if not index or not vector_store or not vector_store._faiss_index:
        logger.error("Index or FAISS vector store unavailable for build. Aborting.")
        return 0, 0

    # Check if index is already populated (via docstore) and not forcing rebuild
    if not force_rebuild and index.docstore and index.docstore.docs:
        doc_count = len(index.docstore.docs)
        vec_count = vector_store._faiss_index.ntotal
        logger.info(
            f"Index already populated (Docstore: {doc_count} docs, FAISS: {vec_count} vectors) and force_rebuild=False. Skipping.")
        return 0, vec_count

    logger.info("Fetching notes from database for indexing...")
    notes_processed_count = 0
    all_llama_documents: List[LlamaDocument] = []
    async for notes_batch in get_all_notes_for_indexing_stream(db,
                                                               batch_size=semantic_retrieval_config.INDEX_BATCH_SIZE):
        if not notes_batch: break
        valid_docs_in_batch = [_db_note_to_llama_doc(n) for n in notes_batch if
                               n.text_content and n.text_content.strip()]
        all_llama_documents.extend(valid_docs_in_batch)
        notes_processed_count += len(notes_batch)
        # logger.debug(f"Fetched batch. DB notes processed: {notes_processed_count}. Valid LlamaDocs: {len(all_llama_documents)}")
        if notes_processed_count >= semantic_retrieval_config.MAX_NOTES_FOR_INITIAL_BUILD:
            logger.warning(
                f"Reached MAX_NOTES_FOR_INITIAL_BUILD ({semantic_retrieval_config.MAX_NOTES_FOR_INITIAL_BUILD}). Stopping.")
            break

    if not all_llama_documents:
        logger.info("No processable notes (with text content) found in DB. Index built/remains empty of new data.")
        persist_index(index, vector_store)  # Persist the (potentially empty but correct) structure
        return notes_processed_count, (vector_store._faiss_index.ntotal if vector_store._faiss_index else 0)

    logger.info(
        f"Building/Populating VectorStoreIndex with {len(all_llama_documents)} LlamaDocuments from {notes_processed_count} DB notes...")

    # The 'index' object here is an empty shell if it was just created, or loaded if exists.
    # Its storage_context contains our IndexFlatL2 vector_store.
    # VectorStoreIndex.from_documents will use this storage_context to populate.
    newly_built_index = VectorStoreIndex.from_documents(
        all_llama_documents,
        storage_context=index.storage_context,  # Use the SC from the loaded/created index
        show_progress=True,
        embed_model=LlamaSettings.embed_model  # Pass the global embed_model
    )
    _vector_index = newly_built_index  # Update global reference

    final_vectors = vector_store._faiss_index.ntotal
    final_docs_in_docstore = len(_vector_index.docstore.docs) if _vector_index.docstore else 0
    logger.info(
        f"Index build complete. DB Notes processed: {notes_processed_count}. "
        f"LlamaDocs indexed: {len(all_llama_documents)}. "
        f"Docs in Docstore: {final_docs_in_docstore}. "
        f"Total vectors in FAISS (IndexFlatL2): {final_vectors}."
    )
    persist_index(_vector_index, vector_store)
    return notes_processed_count, final_vectors


async def rebuild_index_for_user(db: Session, user_id: int) -> Tuple[int, int, str]:
    """Logically deletes user's notes, then re-indexes their current notes using IndexFlatL2."""
    logger.info(f"Rebuilding index for user_id: {user_id}.")

    # Step 1: Logically delete all existing notes for this user from DocStore.
    _, delete_msg, num_targeted_for_delete = await delete_notes_by_user_from_index(db, user_id,
                                                                                   persist_changes=False)  # Don't persist yet
    logger.info(
        f"User notes logical deletion for user {user_id}: {delete_msg} (Targeted {num_targeted_for_delete} DB notes)")

    index = get_vector_index()  # Get the current index (should reflect DocStore deletions)
    if not index:
        msg = f"Index not available after deletion phase for user {user_id}. Rebuild aborted."
        logger.error(msg);
        return 0, 0, msg

    # Step 2: Fetch and re-index current notes for the user.
    notes_reindexed_count = 0  # Count of notes fetched from DB for this user
    docs_for_reindex: List[LlamaDocument] = []
    user_notes_stream = get_notes_by_user_for_indexing_stream(db, owner_id=user_id,
                                                              batch_size=semantic_retrieval_config.INDEX_BATCH_SIZE)
    async for notes_batch in user_notes_stream:
        if not notes_batch: break
        docs_for_reindex.extend(
            [_db_note_to_llama_doc(n) for n in notes_batch if n.text_content and n.text_content.strip()])
        notes_reindexed_count += len(notes_batch)

    nodes_refreshed_count = 0
    if docs_for_reindex:
        logger.info(
            f"Re-indexing {len(docs_for_reindex)} documents for user {user_id} from {notes_reindexed_count} DB notes.")
        # `refresh_ref_docs` will add these to DocStore and add their vectors to FAISS.
        # Since old ones were removed from DocStore, these should mostly be "new" additions to the live index.
        refreshed_doc_ids = index.refresh_ref_docs(docs_for_reindex,
                                                   show_progress=True)  # Use this for robust add/update
        nodes_refreshed_count = sum(len(index.docstore.get_document(doc_id).nodes()) for doc_id in refreshed_doc_ids if
                                    index.docstore.document_exists(doc_id))

    else:
        logger.info(
            f"No current processable notes in DB for user {user_id} to re-index. DocStore reflects prior deletions.")

    persist_index()  # Persist all changes from delete and re-add
    msg = (f"User index rebuild for user {user_id} complete. "
           f"DB Notes targeted for logical delete: {num_targeted_for_delete}. "
           f"DB Notes fetched for re-index: {notes_reindexed_count}. "
           f"LlamaDocs refreshed/added: {len(docs_for_reindex)}. Approx new nodes: {nodes_refreshed_count}.")
    logger.info(msg)
    return notes_reindexed_count, nodes_refreshed_count, msg


def add_note_to_index(note_data: DBNoteForIndexSchema) -> Tuple[bool, str, Optional[str]]:
    """Adds or updates a single note in the index (DocStore update, new vectors to IndexFlatL2)."""
    logger.info(f"Adding/updating note ID {note_data.id} ('{note_data.title}') in index.")
    index = get_vector_index()
    if not index:
        logger.error("Index not available for add_note_to_index.")
        return False, "Index not available.", None

    if not note_data.text_content or not note_data.text_content.strip():
        msg = f"Note ID {note_data.id} has no text content. Not adding to index."
        logger.warning(msg)
        return False, msg, f"note_{note_data.id}"

    llama_doc = _db_note_to_llama_doc(note_data)
    doc_id = llama_doc.doc_id
    try:
        # refresh_ref_docs will remove the old doc_id from DocStore (if exists)
        # and add the new one, then add new vectors to FAISS.
        # With IndexFlatL2, old vectors for this doc_id remain in FAISS physically until full rebuild.
        index.refresh_ref_docs([llama_doc], show_progress=False)
        persist_index()
        msg = f"Note ID {note_data.id} (doc_id: {doc_id}) refreshed in index. DocStore updated, new vectors added to FAISS (IndexFlatL2)."
        logger.info(msg)
        return True, msg, doc_id
    except Exception as e:
        logger.error(f"Error refreshing note ID {note_data.id} (doc_id {doc_id}) in index: {e}", exc_info=True)
        return False, f"Error refreshing note in index: {str(e)}", doc_id


def delete_note_from_index(note_id: int, persist_changes: bool = True) -> Tuple[bool, str, str]:
    """Logically deletes a note by removing it from the DocStore. Vectors in IndexFlatL2 remain."""
    doc_id_to_delete = f"note_{note_id}"
    logger.info(f"Logically deleting note ID {note_id} (doc_id: {doc_id_to_delete}) from DocStore.")
    index = get_vector_index()
    if not index:
        logger.error(f"Index not available for deleting note ID {note_id}.")
        return False, "Index not available.", doc_id_to_delete

    if not index.docstore.document_exists(doc_id_to_delete):
        msg = f"Note ID {note_id} (doc_id: {doc_id_to_delete}) not found in DocStore. Assumed already logically deleted."
        logger.info(msg)
        return True, msg, doc_id_to_delete  # Idempotent

    try:
        # This removes from DocStore. For IndexFlatL2, vector_store.delete() is a no-op or might error softly.
        index.delete_ref_doc(doc_id_to_delete, delete_from_docstore=True)
        if persist_changes: persist_index()
        msg = (f"Note ID {note_id} (doc_id: {doc_id_to_delete}) logically deleted (removed from DocStore). "
               f"Corresponding vectors in FAISS (IndexFlatL2) remain until next full rebuild.")
        logger.info(msg)
        return True, msg, doc_id_to_delete
    except Exception as e:
        logger.warning(f"Issue during logical delete of {doc_id_to_delete} (Note ID {note_id}): {e}. "
                       "Check if DocStore removal was successful despite other issues.")
        if persist_changes: persist_index()  # Persist any partial changes (like if docstore was removed but vs part errored)
        return True, f"Note ID {note_id} (doc_id: {doc_id_to_delete}) processed for logical deletion with potential issues. Details: {e}", doc_id_to_delete


async def delete_notes_by_user_from_index(db: Session, user_id: int, persist_changes: bool = True) -> Tuple[
    bool, str, int]:
    """Logically deletes all notes for a given user by removing them from the DocStore."""
    logger.info(f"Logically deleting all notes for user_id: {user_id} from DocStore.")
    index = get_vector_index()
    if not index:
        logger.error(f"Index not available for deleting notes for user_id {user_id}.")
        return False, "Index not available.", 0

    # Fetch all note IDs for the user from the database to identify target doc_ids
    db_notes_for_user_list: List[DBNoteForIndexSchema] = []
    notes_stream = get_notes_by_user_for_indexing_stream(db, owner_id=user_id, batch_size=500)
    async for notes_batch in notes_stream:
        if not notes_batch: break
        db_notes_for_user_list.extend(notes_batch)

    if not db_notes_for_user_list:
        msg = f"No notes found in DB for user_id: {user_id} to target for logical deletion."
        logger.info(msg)
        return True, msg, 0

    num_db_notes_targeted = len(db_notes_for_user_list)
    deleted_from_docstore_count = 0
    logger.info(f"Targeting {num_db_notes_targeted} DB notes for user {user_id} for logical deletion from DocStore.")

    for note_data in db_notes_for_user_list:
        doc_id = f"note_{note_data.id}"
        if index.docstore.document_exists(doc_id):
            try:
                index.delete_ref_doc(doc_id, delete_from_docstore=True)
                deleted_from_docstore_count += 1
            except Exception as e:
                logger.warning(
                    f"Could not logically delete doc_id {doc_id} (Note ID {note_data.id}) for user {user_id} from DocStore: {e}")

    if deleted_from_docstore_count > 0 and persist_changes:
        persist_index()

    msg = (f"Logical deletion for user {user_id}: {deleted_from_docstore_count} of {num_db_notes_targeted} "
           f"DB notes successfully removed from DocStore. Vectors in FAISS (IndexFlatL2) remain until rebuild.")
    logger.info(msg)
    return True, msg, num_db_notes_targeted


def get_index_statistics() -> Tuple[int, str]:
    """Gets statistics: FAISS vector count, DocStore doc count, FAISS type."""
    try:
        index = get_vector_index()  # Ensures globals _vector_index and _faiss_vector_store are set
        vector_store = _faiss_vector_store

        if not index or not vector_store or not vector_store._faiss_index:
            return 0, "Index or FAISS store not fully initialized or available."

        num_vectors = vector_store._faiss_index.ntotal
        num_docs_in_docstore = len(index.docstore.docs) if index.docstore else 0

        faiss_type_str = "Unknown"
        if isinstance(vector_store._faiss_index, faiss.IndexFlatL2):
            faiss_type_str = "IndexFlatL2 (physical vector deletion via full rebuild)"
        elif isinstance(vector_store._faiss_index, faiss.IndexFlatIP):
            faiss_type_str = "IndexFlatIP (physical vector deletion via full rebuild)"
        elif isinstance(vector_store._faiss_index, faiss.IndexIDMap):
            faiss_type_str = "IndexIDMap (supports vector ID based deletion; not primary strategy here)"
        else:
            faiss_type_str = f"Other ({type(vector_store._faiss_index).__name__})"

        message = (f"FAISS Vectors: {num_vectors}. Docs in Docstore: {num_docs_in_docstore}. "
                   f"Current FAISS Index Type: {faiss_type_str}.")
        return num_vectors, message
    except Exception as e:
        logger.exception("Error retrieving index stats.");
        return 0, f"Error getting stats: {str(e)}"