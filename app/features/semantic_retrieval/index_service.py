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
    # SimpleDirectoryReader, # Not used here, can remove if not planned for file system indexing
    # ServiceContext # Older LlamaIndex, LlamaSettings is preferred
)
from llama_index.llms.openai import OpenAI as LlamaOpenAI # For Qwen Chat LLM
# Import for HuggingFace embeddings
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
# Import for OpenAI/DashScope embeddings (can be commented out if not primary)
# from llama_index.embeddings.openai import OpenAIEmbedding as LlamaOpenAIEmbedding

from llama_index.vector_stores.faiss import FaissVectorStore
from llama_index.core.node_parser import SentenceSplitter
from llama_index.core.storage.docstore import SimpleDocumentStore
from llama_index.core.storage.index_store import SimpleIndexStore

import faiss

from app.core.config import settings as core_settings
from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema
from app.db_connectors.note_reader_service import get_all_notes_for_indexing_stream
from app.features.semantic_retrieval.config import semantic_retrieval_config

logger = logging.getLogger(__name__)

_vector_index: Optional[VectorStoreIndex] = None
_faiss_vector_store: Optional[FaissVectorStore] = None
_llama_settings_initialized: bool = False


def _initialize_llama_index_core_settings():
    global _llama_settings_initialized
    if _llama_settings_initialized and LlamaSettings.llm and LlamaSettings.embed_model:
        logger.debug("LlamaIndex Core Settings already configured.")
        return

    logger.info("Configuring LlamaIndex global settings for semantic retrieval feature...")

    # Configure LLM (Qwen Chat via OpenAI compatible endpoint for LlamaIndex internal tasks)
    try:
        llm = LlamaOpenAI(
            model=core_settings.QWEN_DEFAULT_MODEL,
            api_base=core_settings.QWEN_BASE_URL,
            api_key=core_settings.QWEN_API_KEY,
            temperature=0.1, # Low temperature for internal, deterministic tasks
        )
        LlamaSettings.llm = llm
        logger.info(f"LlamaIndex LLM configured with Qwen model: {core_settings.QWEN_DEFAULT_MODEL}")
    except Exception as e:
        logger.exception(f"Failed to initialize LlamaIndex LLM for semantic retrieval: {e}")
        # Decide if this is critical. For now, log and continue if only embeddings are vital.

    # Configure Embedding Model BASED ON PROVIDER from core_settings
    try:
        if core_settings.EMBEDDING_MODEL_PROVIDER == "huggingface":
            LlamaSettings.embed_model = HuggingFaceEmbedding(
                model_name=core_settings.HF_EMBEDDING_MODEL_NAME
            )
            logger.info(
                f"LlamaIndex Embed Model configured with HuggingFace: {core_settings.HF_EMBEDDING_MODEL_NAME} "
                f"(Expected Dim: {core_settings.ACTIVE_EMBEDDING_DIMENSION})"
            )
        # elif core_settings.EMBEDDING_MODEL_PROVIDER == "dashscope":
            # from llama_index.embeddings.openai import OpenAIEmbedding as LlamaOpenAIEmbedding # Ensure import
            # LlamaSettings.embed_model = LlamaOpenAIEmbedding(
            #     model_name=core_settings.DASHSCOPE_EMBEDDING_MODEL_NAME, # Ensure this is defined in core_settings
            #     api_base=core_settings.QWEN_BASE_URL,
            #     api_key=core_settings.QWEN_API_KEY,
            #     dimensions=core_settings.ACTIVE_EMBEDDING_DIMENSION
            # )
            # logger.info(
            #     f"LlamaIndex Embed Model configured with DashScope: {core_settings.DASHSCOPE_EMBEDDING_MODEL_NAME} "
            #     f"(Dim: {core_settings.ACTIVE_EMBEDDING_DIMENSION})"
            # )
        else:
            err_msg = f"Unsupported EMBEDDING_MODEL_PROVIDER: '{core_settings.EMBEDDING_MODEL_PROVIDER}' in core_settings."
            logger.error(err_msg)
            raise ValueError(err_msg) # Critical if no embed model can be set

    except Exception as e:
        logger.exception(f"CRITICAL: Failed to initialize LlamaIndex Embedding Model: {e}")
        raise

    LlamaSettings.chunk_size = semantic_retrieval_config.DEFAULT_CHUNK_SIZE
    LlamaSettings.chunk_overlap = semantic_retrieval_config.DEFAULT_CHUNK_OVERLAP
    logger.info(
        f"LlamaIndex chunk_size: {LlamaSettings.chunk_size}, chunk_overlap: {LlamaSettings.chunk_overlap} (from semantic_retrieval_config)")
    _llama_settings_initialized = True


def _db_note_to_llama_doc(note_data: DBNoteForIndexSchema) -> LlamaDocument:
    doc_id = f"note_{note_data.id}"
    metadata = {
        "note_id": str(note_data.id),
        "title": str(note_data.title or "Untitled"),
        "creation_date": str(note_data.creation_date.isoformat() if note_data.creation_date else ""),
        "owner_id": str(note_data.owner_id),
        "source_type": "note"
    }
    text_content = note_data.text_content if note_data.text_content is not None else ""
    if not text_content.strip():
        logger.debug(
            f"Note ID {note_data.id} ('{note_data.title}') has no text content. Creating LlamaDocument with a placeholder space.")
        text_content = " "
    return LlamaDocument(text=text_content, doc_id=doc_id, metadata=metadata)


def get_faiss_vector_store(recreate: bool = False) -> FaissVectorStore:
    global _faiss_vector_store
    _initialize_llama_index_core_settings() # Ensures embed model is ready for dimension check

    if _faiss_vector_store and not recreate:
        return _faiss_vector_store

    faiss_index_path_obj = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
    embedding_dim = core_settings.ACTIVE_EMBEDDING_DIMENSION # Use the dynamically set active dimension

    if faiss_index_path_obj.exists() and not recreate:
        logger.info(f"Loading FAISS index from: {faiss_index_path_obj}")
        try:
            faiss_index = faiss.read_index(str(faiss_index_path_obj))
            if faiss_index.d != embedding_dim:
                logger.error(
                    f"FAISS index dimension mismatch! Disk: {faiss_index.d}, Active Config: {embedding_dim}. "
                    f"Deleting and recreating index at {faiss_index_path_obj}."
                )
                faiss_index_path_obj.unlink(missing_ok=True)
                for f in core_settings.VECTOR_STORE_PATH.glob("*.json"): f.unlink(missing_ok=True)
                # Fall through to create new index after cleanup
                faiss_index_instance = faiss.IndexFlatL2(embedding_dim)
                _faiss_vector_store = FaissVectorStore(faiss_index=faiss_index_instance)
                logger.info(f"Created new empty FAISS vector store (dim: {embedding_dim}) due to dimension mismatch.")
            else:
                _faiss_vector_store = FaissVectorStore(faiss_index=faiss_index)
                logger.info(f"FAISS index loaded successfully with {faiss_index.ntotal} vectors.")
        except Exception as e:
            logger.warning(
                f"Failed to load FAISS index from {faiss_index_path_obj} (Error: {e}). Will create a new one with dim {embedding_dim}.")
            faiss_index_instance = faiss.IndexFlatL2(embedding_dim)
            _faiss_vector_store = FaissVectorStore(faiss_index=faiss_index_instance)
    else:
        if recreate:
            logger.info(f"Recreating FAISS vector store (dim: {embedding_dim}).")
        else:
            logger.info(f"FAISS index file not found at {faiss_index_path_obj}. Creating new (dim: {embedding_dim}).")
        faiss_index_instance = faiss.IndexFlatL2(embedding_dim)
        _faiss_vector_store = FaissVectorStore(faiss_index=faiss_index_instance)

    return _faiss_vector_store


def get_vector_index(recreate_faiss: bool = False) -> VectorStoreIndex:
    global _vector_index
    _initialize_llama_index_core_settings()

    if _vector_index and not recreate_faiss:
        return _vector_index

    vector_store = get_faiss_vector_store(recreate=recreate_faiss)
    storage_context_path = core_settings.VECTOR_STORE_PATH
    docstore_path = storage_context_path / "docstore.json" # Common LlamaIndex storage file

    try:
        if not recreate_faiss and docstore_path.exists():
            logger.info(f"Attempting to load VectorStoreIndex from LlamaIndex storage: {storage_context_path}...")
            # Load all components of the storage context from the persist_dir
            storage_context = StorageContext.from_defaults(
                vector_store=vector_store, # Pass the vector_store we already loaded/created
                persist_dir=str(storage_context_path)
            )
            _vector_index = load_index_from_storage(storage_context)
            # Small verification
            if _vector_index and _vector_index.vector_store:
                 vs_in_idx = _vector_index.vector_store._faiss_index # type: ignore
                 if vs_in_idx.ntotal != vector_store._faiss_index.ntotal:
                     logger.warning(f"Post-load vector count mismatch. FAISS direct: {vector_store._faiss_index.ntotal}, Index's VS: {vs_in_idx.ntotal}")
            logger.info(f"Successfully loaded VectorStoreIndex. FAISS has {vector_store._faiss_index.ntotal} vectors.")
        else:
            if recreate_faiss:
                logger.info("FAISS store was recreated. Initializing new empty VectorStoreIndex structure.")
            else:
                logger.info("No existing LlamaIndex metadata (docstore.json). Initializing new empty VectorStoreIndex structure.")
            storage_context = StorageContext.from_defaults(vector_store=vector_store)
            _vector_index = VectorStoreIndex.from_documents(
                [], # Start with no documents for an empty index shell
                storage_context=storage_context,
            )
            logger.info("Initialized new empty VectorStoreIndex structure.")
    except Exception as e:
        logger.error(f"Error loading or initializing VectorStoreIndex: {e}. Attempting fallback to basic empty index.", exc_info=True)
        storage_context = StorageContext.from_defaults(vector_store=vector_store) # Ensure fresh context on error
        _vector_index = VectorStoreIndex.from_documents([], storage_context=storage_context)
        logger.info("Fallback: Initialized basic new empty VectorStoreIndex structure due to error.")

    return _vector_index


def persist_index(index_to_persist: Optional[VectorStoreIndex] = None,
                  vector_store_to_persist: Optional[FaissVectorStore] = None):
    idx = index_to_persist if index_to_persist is not None else _vector_index
    vs = vector_store_to_persist if vector_store_to_persist is not None else _faiss_vector_store


    if not idx: # Check if idx is None after assignment
        logger.error("Cannot persist index: _vector_index is None.")
        return
    if not vs: # Check if vs is None after assignment
        logger.error("Cannot persist index: _faiss_vector_store is None.")
        return


    try:
        faiss_path = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
        faiss.write_index(vs._faiss_index, str(faiss_path))
        logger.info(f"FAISS index persisted to {faiss_path}")

        idx.storage_context.persist(persist_dir=str(core_settings.VECTOR_STORE_PATH))
        logger.info(f"LlamaIndex storage context persisted to {core_settings.VECTOR_STORE_PATH}")
    except Exception as e:
        logger.exception(f"Error during index persistence: {e}")


async def build_full_index(db: Session, force_rebuild: bool = False) -> Tuple[int, int]:
    global _vector_index, _faiss_vector_store

    logger.info(f"Starting full index build. Force rebuild: {force_rebuild}")

    if force_rebuild:
        logger.info("Force_rebuild is True. Clearing existing index data...")
        faiss_path = core_settings.VECTOR_STORE_PATH / core_settings.FAISS_INDEX_FILENAME_DEFAULT
        if faiss_path.exists(): faiss_path.unlink(missing_ok=True)
        for f_path in core_settings.VECTOR_STORE_PATH.glob("*.json"): f_path.unlink(missing_ok=True)

        _faiss_vector_store = None # Will be recreated by get_faiss_vector_store
        _vector_index = None       # Will be recreated by get_vector_index

    # This call will ensure LlamaSettings are initialized, FAISS store is loaded/created,
    # and an empty VectorStoreIndex shell is ready if needed.
    # It will also handle the 'recreate_faiss' logic for get_faiss_vector_store
    index = get_vector_index(recreate_faiss=force_rebuild)
    vector_store = _faiss_vector_store # get_faiss_vector_store updates the global _faiss_vector_store

    if not vector_store or not index: # Should not happen if get_vector_index is robust
        logger.error("Failed to obtain valid index or vector store for building.")
        return 0,0

    initial_vector_count = vector_store._faiss_index.ntotal
    if not force_rebuild and initial_vector_count > 0:
        logger.info(
            f"Index already exists with {initial_vector_count} vectors. Skipping initial full build unless forced.")
        return 0, initial_vector_count

    logger.info("Proceeding with full index build from database notes...")
    notes_processed_count = 0
    all_llama_documents: List[LlamaDocument] = []
    async for notes_batch in get_all_notes_for_indexing_stream(db,
                                                               batch_size=semantic_retrieval_config.INDEX_BATCH_SIZE):
        if not notes_batch: break
        batch_llama_docs = [_db_note_to_llama_doc(note) for note in notes_batch if
                            note.text_content and note.text_content.strip()]
        all_llama_documents.extend(batch_llama_docs)
        notes_processed_count += len(notes_batch)
        logger.info(f"Fetched batch of {len(notes_batch)} notes. Total notes processed so far: {notes_processed_count}")
        if notes_processed_count >= semantic_retrieval_config.MAX_NOTES_FOR_INITIAL_BUILD:
            logger.warning(
                f"Reached MAX_NOTES_FOR_INITIAL_BUILD ({semantic_retrieval_config.MAX_NOTES_FOR_INITIAL_BUILD}). Stopping build.")
            break

    if not all_llama_documents:
        logger.info("No processable notes (with text) found in the database to build the index.")
        persist_index(index, vector_store)
        return 0, vector_store._faiss_index.ntotal

    logger.info(
        f"Total of {len(all_llama_documents)} LlamaDocuments prepared for indexing from {notes_processed_count} notes.")

    # If we are here, it means initial_vector_count was 0 or force_rebuild was true.
    # The index object we have should be an empty shell, ready to be built.
    logger.info("Constructing/Populating VectorStoreIndex from documents...")
    # We pass the existing storage_context from the (potentially empty) index.
    # VectorStoreIndex.from_documents will populate this storage_context.
    newly_built_index = VectorStoreIndex.from_documents(
        all_llama_documents,
        storage_context=index.storage_context, # Use the storage_context from the loaded/created index
        show_progress=True
    )
    _vector_index = newly_built_index # Update the global reference to the newly built index

    final_vector_count = vector_store._faiss_index.ntotal # vector_store is part of index.storage_context
    logger.info(
        f"Index build complete. Notes processed: {notes_processed_count}. Total vectors in FAISS: {final_vector_count}")

    persist_index(_vector_index, vector_store)
    return notes_processed_count, final_vector_count


def add_note_to_index(note_data: DBNoteForIndexSchema) -> Tuple[bool, str, Optional[str]]:
    logger.info(f"Request to add/update note ID {note_data.id} ('{note_data.title}') in index.")
    index = get_vector_index() # Ensures index is available

    llama_doc = _db_note_to_llama_doc(note_data)

    # For adding/updating individual documents, parsing nodes first is more explicit
    parser = SentenceSplitter.from_defaults()
    nodes_to_insert = parser.get_nodes_from_documents([llama_doc])

    if not nodes_to_insert:
        msg = f"No nodes generated for note ID {note_data.id}. Note not added to index."
        logger.warning(msg)
        return False, msg, llama_doc.doc_id

    try:
        # Delete existing nodes for this doc_id to handle updates
        index.delete_ref_doc(llama_doc.doc_id, delete_from_docstore=True)
        logger.info(f"Successfully deleted existing nodes for doc_id '{llama_doc.doc_id}' before update/insert.")
    except Exception:
        # This is expected if the document is new
        logger.debug(f"No existing nodes found for doc_id '{llama_doc.doc_id}' (likely a new note).")

    index.insert_nodes(nodes_to_insert) # Insert the new/updated nodes
    persist_index() # Persist changes
    msg = f"Note ID {note_data.id} (doc_id: {llama_doc.doc_id}) processed and added/updated in index."
    logger.info(msg)
    return True, msg, llama_doc.doc_id


def delete_note_from_index(note_id: int) -> Tuple[bool, str, str]:
    doc_id_to_delete = f"note_{note_id}"
    logger.info(f"Request to delete note ID {note_id} (doc_id: {doc_id_to_delete}) from index.")
    index = get_vector_index() # Ensures index is available

    try:
        index.delete_ref_doc(doc_id_to_delete, delete_from_docstore=True)
        persist_index() # Persist changes
        msg = f"Note ID {note_id} (doc_id: {doc_id_to_delete}) successfully deleted from index."
        logger.info(msg)
        return True, msg, doc_id_to_delete
    except Exception as e:
        msg = f"Failed to delete note ID {note_id} (doc_id: {doc_id_to_delete}) from index: {e}. It might not have been indexed."
        logger.warning(msg)
        return False, msg, doc_id_to_delete


def get_index_statistics() -> Tuple[int, str]:
    try:
        # Ensure index and faiss_vector_store are initialized by calling get_vector_index
        get_vector_index() # This initializes _faiss_vector_store through its chain of calls
        if _faiss_vector_store and _faiss_vector_store._faiss_index:
            count = _faiss_vector_store._faiss_index.ntotal
            return count, "Statistics retrieved successfully."
        else:
            # This state might occur if get_vector_index() itself fails catastrophically before _faiss_vector_store is set
            logger.warning("_faiss_vector_store is not initialized when trying to get stats.")
            return 0, "Index or FAISS store not available (failed to initialize)."
    except Exception as e:
        logger.exception("Error retrieving index statistics.")
        return 0, f"Error retrieving statistics: {str(e)}"