# app/index_service.py
import logging
from typing import List, Optional, Tuple, cast

# LlamaIndex and FAISS imports
from llama_index.core import Document as LlamaDocument, VectorStoreIndex, Settings as LlamaSettings
from .llama_ops.custom_faiss_vstore import CustomFaissVectorStore # CHANGED

# Local application imports (no more direct db connectors)
from .config import settings  # CHANGED
from .schemas import NoteForIndex as DBNoteForIndexSchema # CHANGED
from .clients.database_client import database_client # CHANGED
from .llama_ops import ( # CHANGED
    initialize_llama_index_settings,
    db_note_to_llama_document,
    ensure_vector_index,
    persist_index_and_vector_store,
    clear_index_storage_completely,
    refresh_document_in_index,
    get_global_vector_index,
    get_global_faiss_vector_store,
    get_faiss_index_type_description,
)
from .llama_ops.indexing_ops import remove_document_from_index # CHANGED

logger = logging.getLogger(__name__)


def _get_active_index_and_store() -> Tuple[Optional[VectorStoreIndex], Optional[CustomFaissVectorStore]]:
    """Initializes LlamaIndex settings and returns the active global index and vector store instances."""
    initialize_llama_index_settings()
    index = ensure_vector_index()
    vector_store = get_global_faiss_vector_store()
    if not index or not vector_store or not vector_store._faiss_index:  # type: ignore
        logger.error("Index service: Index or FAISS vector store (or its internal faiss_index) unavailable.")
        return None, None
    return index, cast(CustomFaissVectorStore, vector_store)


async def build_full_index(force_rebuild: bool = False) -> Tuple[int, int]:
    """
    Builds the vector index from scratch by fetching all notes from the database-api service.
    This function is now fully independent of any direct database connection.
    """
    logger.info(f"Index service: Full index build started. Force rebuild: {force_rebuild}")
    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store:
        logger.error("Index service: Failed to get or create active index/vector store for full build.")
        return 0, 0

    if not force_rebuild and index.docstore and len(index.docstore.docs) > 0:
        doc_count = len(index.docstore.docs)
        vec_count = vector_store._faiss_index.ntotal  # type: ignore
        logger.info(
            f"Index service: Index already populated (Docs: {doc_count}, Vectors: {vec_count}) "
            f"and force_rebuild=False. Skipping build."
        )
        return 0, vec_count

    if force_rebuild:
        clear_index_storage_completely()
        index, vector_store = _get_active_index_and_store()
        if not index or not vector_store:
            logger.error("Index service: Failed to re-initialize index/vector store after clearing.")
            return 0, 0

    logger.info("Index service: Fetching notes from database-api for indexing...")
    notes_processed_count = 0
    all_llama_documents: List[LlamaDocument] = []

    # Use the database API client to stream notes and re-batch them locally.
    notes_batch: List[DBNoteForIndexSchema] = []
    async for note in database_client.stream_all_notes():
        notes_batch.append(note)

        if len(notes_batch) >= settings.INDEX_BATCH_SIZE:
            valid_docs = [db_note_to_llama_document(n) for n in notes_batch if
                          n.text_content and n.text_content.strip()]
            all_llama_documents.extend(valid_docs)
            notes_processed_count += len(notes_batch)
            logger.info(f"Processed batch of {len(notes_batch)} notes. Total processed: {notes_processed_count}")
            notes_batch = []  # Reset batch

        if notes_processed_count >= settings.MAX_NOTES_FOR_INITIAL_BUILD:
            logger.warning(
                f"Reached MAX_NOTES_FOR_INITIAL_BUILD ({settings.MAX_NOTES_FOR_INITIAL_BUILD}). Stopping stream.")
            break

    # Process any remaining notes in the final batch
    if notes_batch:
        valid_docs = [db_note_to_llama_document(n) for n in notes_batch if n.text_content and n.text_content.strip()]
        all_llama_documents.extend(valid_docs)
        notes_processed_count += len(notes_batch)
        logger.info(f"Processed final batch of {len(notes_batch)} notes. Total processed: {notes_processed_count}")

    if not all_llama_documents:
        logger.info("Index service: No processable notes found from database-api. Index may be empty.")
        persist_index_and_vector_store(index, vector_store)
        return notes_processed_count, (
            vector_store._faiss_index.ntotal if vector_store._faiss_index else 0)  # type: ignore

    logger.info(f"Index service: Populating index with {len(all_llama_documents)} LlamaDocuments...")
    try:
        index.insert_nodes(all_llama_documents, show_progress=True)
        logger.info(f"Index service: Successfully inserted {len(all_llama_documents)} documents.")
    except Exception as e:
        logger.error(f"Index service: Error during insert_nodes: {e}", exc_info=True)
        persist_index_and_vector_store(index, vector_store)
        raise

    final_vectors = vector_store._faiss_index.ntotal  # type: ignore
    final_docs = len(index.docstore.docs) if index.docstore else 0
    logger.info(
        f"Index build complete. Notes processed: {notes_processed_count}. "
        f"LlamaDocs indexed: {len(all_llama_documents)}. Docs in Docstore: {final_docs}. "
        f"Total vectors in FAISS: {final_vectors}."
    )
    persist_index_and_vector_store(index, vector_store)
    return notes_processed_count, final_vectors


def add_or_update_note_in_index(note_data: DBNoteForIndexSchema) -> Tuple[bool, str, Optional[str]]:
    """Adds or updates a single note document in the index."""
    logger.info(f"Index service: Adding/updating note ID {note_data.id} in index.")
    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store:
        return False, "Index service: Index/vector store not available.", None

    if not note_data.text_content or not note_data.text_content.strip():
        msg = f"Note ID {note_data.id} has no text content. Removing from index if it exists."
        logger.warning(msg)
        doc_id_to_check = f"note_{note_data.id}"
        if index.docstore.document_exists(doc_id_to_check):
            if remove_document_from_index(index, doc_id_to_check):
                persist_index_and_vector_store(index, vector_store)
                return True, f"Note ID {note_data.id} had no content and was removed.", doc_id_to_check
            else:
                return False, f"Note ID {note_data.id} had no content but failed removal.", doc_id_to_check
        return True, "Note had no content and was not in the index.", doc_id_to_check

    llama_doc = db_note_to_llama_document(note_data)
    success = refresh_document_in_index(index, llama_doc)

    if success:
        persist_index_and_vector_store(index, vector_store)
        msg = f"Note ID {note_data.id} (doc_id: {llama_doc.id_}) processed successfully."
        logger.info(msg)
        return True, msg, llama_doc.id_
    else:
        msg = f"Failed to process note ID {note_data.id} (doc_id: {llama_doc.id_}) in index."
        logger.error(msg)
        return False, msg, llama_doc.id_


def get_index_statistics() -> dict:
    """Retrieves detailed statistics about the current vector index and its configuration."""
    index, vector_store = _get_active_index_and_store()

    if not index or not vector_store or not hasattr(vector_store, '_faiss_index') or not vector_store._faiss_index:
        return {"total_indexed_vectors": 0, "message": "Index or FAISS store not fully initialized."}

    try:
        num_vectors = vector_store._faiss_index.ntotal
        num_docs = len(index.docstore.docs) if index.docstore else 0
        faiss_type = get_faiss_index_type_description(vector_store)
        faiss_dim = vector_store._faiss_index.d if hasattr(vector_store._faiss_index, 'd') else None

        embed_model = LlamaSettings.embed_model
        embed_model_name = getattr(embed_model, 'model_name', type(embed_model).__name__) if embed_model else "N/A"

        return {
            "total_indexed_vectors": num_vectors,
            "num_docs_in_docstore": num_docs,
            "faiss_index_type": faiss_type,
            "faiss_index_dimension": faiss_dim,
            "llama_configured_chunk_size": LlamaSettings.chunk_size,
            "llama_configured_chunk_overlap": LlamaSettings.chunk_overlap,
            "llama_embedding_model_name": embed_model_name,
            "index_storage_path": str(settings.VECTOR_STORE_PATH.resolve()),
            "message": "Index statistics retrieved successfully."
        }
    except Exception as e:
        logger.exception("Error retrieving detailed index stats.")
        return {"total_indexed_vectors": 0, "message": f"Error getting stats: {e}"}


def delete_note_from_index(note_id: int) -> Tuple[bool, str, Optional[str]]:
    """Deletes a note and its vectors from the index using its database ID."""
    doc_id_to_delete = f"note_{note_id}"
    logger.info(f"Index service: Attempting to delete doc_id {doc_id_to_delete} from index.")

    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store:
        msg = f"Index/vector store not available for deletion of doc_id {doc_id_to_delete}."
        logger.error(msg)
        return False, msg, doc_id_to_delete

    if not index.docstore.document_exists(doc_id_to_delete):
        msg = f"Document {doc_id_to_delete} not in index. Deletion is considered successful (idempotent)."
        logger.info(msg)
        return True, msg, doc_id_to_delete

    if remove_document_from_index(index, doc_id_to_delete):
        persist_index_and_vector_store(index, vector_store)
        msg = f"Successfully deleted doc_id {doc_id_to_delete} from index."
        logger.info(msg)
        return True, msg, doc_id_to_delete
    else:
        persist_index_and_vector_store(index, vector_store)
        msg = f"Failed to delete doc_id {doc_id_to_delete} from index."
        logger.error(msg)
        return False, msg, doc_id_to_delete