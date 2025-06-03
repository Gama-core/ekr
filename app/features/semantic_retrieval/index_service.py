# app/features/semantic_retrieval/index_service.py
import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
from llama_index.core import Document as LlamaDocument, VectorStoreIndex, \
    Settings as LlamaSettings  # Added LlamaSettings
from llama_index.vector_stores.faiss import FaissVectorStore

from app.db_connectors.schemas import NoteForIndex as DBNoteForIndexSchema
from app.db_connectors.note_reader_service import get_all_notes_for_indexing_stream
from app.features.semantic_retrieval.config import semantic_retrieval_config
from app.features.semantic_retrieval.llama_ops import (
    initialize_llama_index_settings,
    db_note_to_llama_document,
    ensure_vector_index,
    persist_index_and_vector_store,
    clear_index_storage_completely,
    refresh_document_in_index,
    get_global_vector_index,
    get_global_faiss_vector_store,
    get_faiss_index_type_description,
    set_global_vector_index
)
from app.core.config import settings as core_settings  # Added core_settings

logger = logging.getLogger(__name__)


def _get_active_index_and_store() -> Tuple[Optional[VectorStoreIndex], Optional[FaissVectorStore]]:
    initialize_llama_index_settings()  # This ensures LlamaSettings are populated
    index = ensure_vector_index()
    vector_store = get_global_faiss_vector_store()
    if not index or not vector_store or not vector_store._faiss_index:
        logger.error("Index service: Index or FAISS vector store (or its internal faiss_index) unavailable.")
        return None, None
    return index, vector_store


async def build_full_index(db: Session, force_rebuild: bool = False) -> Tuple[int, int]:
    logger.info(f"Index service: Full index build started. Force rebuild: {force_rebuild}")
    index, vector_store = _get_active_index_and_store()  # This will also initialize LlamaSettings
    if not index or not vector_store:
        logger.error("Index service: Failed to get or create active index/vector store for full build.")
        return 0, 0

    # If not forcing rebuild and index already has documents, skip.
    if not force_rebuild and index.docstore and len(index.docstore.docs) > 0:
        doc_count = len(index.docstore.docs)
        vec_count = vector_store._faiss_index.ntotal
        logger.info(
            f"Index service: Index already populated (Docstore: {doc_count} docs, FAISS: {vec_count} vectors) "
            f"and force_rebuild=False. Skipping full build process."
        )
        return 0, vec_count

    # If forcing rebuild, clear storage first
    if force_rebuild:
        clear_index_storage_completely()
        # Re-initialize after clearing to get fresh instances
        index, vector_store = _get_active_index_and_store()
        if not index or not vector_store:
            logger.error(
                "Index service: Failed to re-initialize active index/vector store after clearing for full build.")
            return 0, 0

    logger.info("Index service: Fetching notes from database for indexing...")
    notes_processed_count = 0
    all_llama_documents: List[LlamaDocument] = []
    async for notes_batch in get_all_notes_for_indexing_stream(db,
                                                               batch_size=semantic_retrieval_config.INDEX_BATCH_SIZE):
        if not notes_batch: break
        valid_docs_in_batch = [
            db_note_to_llama_document(n) for n in notes_batch if n.text_content and n.text_content.strip()
        ]
        all_llama_documents.extend(valid_docs_in_batch)
        notes_processed_count += len(notes_batch)
        if notes_processed_count >= semantic_retrieval_config.MAX_NOTES_FOR_INITIAL_BUILD:
            logger.warning(
                f"Index service: Reached MAX_NOTES_FOR_INITIAL_BUILD ({semantic_retrieval_config.MAX_NOTES_FOR_INITIAL_BUILD}). Stopping.")
            break

    if not all_llama_documents:
        logger.info("Index service: No processable notes found in DB for full build. Index may be empty.")
        persist_index_and_vector_store(index, vector_store)
        return notes_processed_count, (vector_store._faiss_index.ntotal if vector_store._faiss_index else 0)

    logger.info(
        f"Index service: Populating VectorStoreIndex with {len(all_llama_documents)} LlamaDocuments "
        f"from {notes_processed_count} DB notes..."
    )
    try:
        # Using insert_nodes which is more direct for adding documents to an existing index structure
        # This internally handles node parsing based on LlamaSettings.chunk_size, etc.
        # and then adds them to the vector store.
        index.insert_nodes(all_llama_documents)
        logger.info(f"Index service: Successfully inserted {len(all_llama_documents)} documents.")
    except Exception as e:
        logger.error(f"Index service: Error during insert_nodes: {e}", exc_info=True)
        persist_index_and_vector_store(index, vector_store)
        raise

    final_vectors = vector_store._faiss_index.ntotal
    final_docs_in_docstore = len(index.docstore.docs) if index.docstore else 0
    logger.info(
        f"Index service: Index build complete. DB Notes processed: {notes_processed_count}. "
        f"LlamaDocs indexed: {len(all_llama_documents)}. "
        f"Docs in Docstore: {final_docs_in_docstore}. "
        f"Total vectors in FAISS ({get_faiss_index_type_description(vector_store)}): {final_vectors}."
    )
    persist_index_and_vector_store(index, vector_store)
    return notes_processed_count, final_vectors


def add_or_update_note_in_index(note_data: DBNoteForIndexSchema) -> Tuple[bool, str, Optional[str]]:
    logger.info(f"Index service: Adding/updating note ID {note_data.id} ('{note_data.title}') in index.")
    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store:
        return False, "Index service: Index/vector store not available.", None

    if not note_data.text_content or not note_data.text_content.strip():
        msg = f"Index service: Note ID {note_data.id} has no text content. Not adding to index."
        logger.warning(msg)
        doc_id_to_check = f"note_{note_data.id}"
        if index.docstore.document_exists(doc_id_to_check):
            logger.info(
                f"Index service: Note {doc_id_to_check} previously existed and now has no content. Attempting removal.")
            from app.features.semantic_retrieval.llama_ops.indexing_ops import \
                remove_document_from_index
            removal_success = remove_document_from_index(index, doc_id_to_check)
            if removal_success:
                persist_index_and_vector_store(index, vector_store)
                return True, f"Note ID {note_data.id} had no content and was removed from index.", doc_id_to_check
            else:
                return False, f"Note ID {note_data.id} had no content but failed to be removed from index.", doc_id_to_check
        return False, msg, doc_id_to_check

    llama_doc = db_note_to_llama_document(note_data)
    doc_id = llama_doc.id_  # Using id_ as per LlamaIndex convention

    success = refresh_document_in_index(index, llama_doc)

    if success:
        persist_index_and_vector_store(index, vector_store)
        msg = f"Index service: Note ID {note_data.id} (doc_id: {doc_id}) processed (added/updated) in index."
        logger.info(msg)
        return True, msg, doc_id
    else:
        msg = f"Index service: Failed to process (add/update) note ID {note_data.id} (doc_id: {doc_id}) in index."
        logger.error(msg)
        return False, msg, doc_id


def get_index_statistics() -> dict:  # Changed return type to dict to match new schema structure
    index, vector_store = _get_active_index_and_store()  # This also initializes LlamaSettings

    if not index or not vector_store or not hasattr(vector_store, '_faiss_index') or not vector_store._faiss_index:
        logger.info("Index service stats: globals not found or index not fully initialized.")
        # Attempt to initialize/load index again if needed, though _get_active_index_and_store should handle it.
        # For simplicity, we rely on the initial call.
        return {
            "total_indexed_vectors": 0,
            "message": "Index service: Index or FAISS store not fully initialized or available."
        }

    try:
        num_vectors = vector_store._faiss_index.ntotal
        num_docs_in_docstore = len(index.docstore.docs) if index.docstore else 0
        faiss_type_str = get_faiss_index_type_description(vector_store)
        faiss_dimension = vector_store._faiss_index.d if hasattr(vector_store._faiss_index, 'd') else None

        # Get LlamaSettings details
        # initialize_llama_index_settings() # ensure settings are loaded if not already by _get_active_index_and_store

        configured_chunk_size = LlamaSettings.chunk_size
        configured_chunk_overlap = LlamaSettings.chunk_overlap

        embedding_model_name = "N/A"
        if LlamaSettings.embed_model:
            if hasattr(LlamaSettings.embed_model, 'model_name'):
                embedding_model_name = LlamaSettings.embed_model.model_name
            else:  # Fallback for other embedder types
                embedding_model_name = type(LlamaSettings.embed_model).__name__

        # llm_model_name = "N/A"
        # if LlamaSettings.llm and hasattr(LlamaSettings.llm, 'model'):
        #     llm_model_name = LlamaSettings.llm.model

        storage_path = str(core_settings.VECTOR_STORE_PATH.resolve())

        stats_data = {
            "total_indexed_vectors": num_vectors,
            "num_docs_in_docstore": num_docs_in_docstore,
            "faiss_index_type": faiss_type_str,
            "faiss_index_dimension": faiss_dimension,
            "llama_configured_chunk_size": configured_chunk_size,
            "llama_configured_chunk_overlap": configured_chunk_overlap,
            "llama_embedding_model_name": embedding_model_name,
            # "llama_llm_model_name": llm_model_name,
            "index_storage_path": storage_path,
            "message": (
                f"FAISS Vectors: {num_vectors}. Docs in Docstore: {num_docs_in_docstore}. "
                f"FAISS Type: {faiss_type_str}. Dimension: {faiss_dimension}. "
                f"ChunkSize: {configured_chunk_size}. EmbedModel: {embedding_model_name}."
            )
        }
        return stats_data

    except Exception as e:
        logger.exception("Index service: Error retrieving detailed index stats.")
        return {
            "total_indexed_vectors": 0,  # Provide default on error
            "message": f"Error getting stats: {str(e)}"
        }