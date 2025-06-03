# app/features/semantic_retrieval/index_service.py
import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm import Session
# Make sure LlamaSettings is imported if you use LlamaSettings.embed_model directly
from llama_index.core import Document as LlamaDocument, VectorStoreIndex, Settings as LlamaSettings

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
    set_global_vector_index  # Import the setter
)

logger = logging.getLogger(__name__)


def _get_active_index_and_store() -> Tuple[Optional[VectorStoreIndex], Optional[FaissVectorStore]]:
    initialize_llama_index_settings()
    index = ensure_vector_index()
    vector_store = get_global_faiss_vector_store()
    if not index or not vector_store or not vector_store._faiss_index:
        logger.error("Index service: Index or FAISS vector store (or its internal faiss_index) unavailable.")
        return None, None
    return index, vector_store


async def build_full_index(db: Session, force_rebuild: bool = False) -> Tuple[int, int]:
    logger.info(f"Index service: Full index build started. Force rebuild: {force_rebuild}")
    initialize_llama_index_settings()

    if force_rebuild:
        clear_index_storage_completely()

    index, vector_store = _get_active_index_and_store()
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
        persist_index_and_vector_store(index, vector_store)  # Persist the (potentially empty) index structure
        return notes_processed_count, (vector_store._faiss_index.ntotal if vector_store._faiss_index else 0)

    logger.info(
        f"Index service: Populating VectorStoreIndex with {len(all_llama_documents)} LlamaDocuments "
        f"from {notes_processed_count} DB notes..."
    )


    # Instead of VectorStoreIndex.from_documents directly on a potentially new StorageContext,
    # ensure we are using the already initialized index object (which should be empty if rebuilding)
    # and insert nodes into it.

    # The 'index' variable here *is* our newly_built_index if force_rebuild was true or if it was loaded empty.
    # If it was loaded with data and force_rebuild=false, we wouldn't reach this point.

    if all_llama_documents:
        logger.info(f"Index service: Inserting {len(all_llama_documents)} documents into the index...")
        # Process in batches to manage memory and potentially work around issues
        # LlamaIndex's insert_nodes should handle batching internally if implemented by the vector store,
        # but explicit batching here can also help manage progress logs or memory for very large lists of documents.
        # For now, let's try inserting all at once, as insert_nodes should delegate to vector_store.add which processes in batches.
        try:
            index.insert_nodes(all_llama_documents)  # This calls vector_store.add()
            logger.info(f"Index service: Successfully inserted {len(all_llama_documents)} documents.")
        except Exception as e:
            logger.error(f"Index service: Error during insert_nodes: {e}", exc_info=True)
            # Persist whatever might have been partially indexed before erroring
            persist_index_and_vector_store(index, vector_store)
            raise  # Re-raise the exception to indicate build failure

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
        # If the note previously existed and now has no content, we should remove it.
        # This uses the remove_document_from_index which relies on LlamaIndex's delete_ref_doc.
        doc_id_to_check = f"note_{note_data.id}"
        if index.docstore.document_exists(doc_id_to_check):
            logger.info(
                f"Index service: Note {doc_id_to_check} previously existed and now has no content. Attempting removal.")
            from app.features.semantic_retrieval.llama_ops.indexing_ops import \
                remove_document_from_index  # Direct import for clarity
            removal_success = remove_document_from_index(index, doc_id_to_check)
            if removal_success:
                persist_index_and_vector_store(index, vector_store)
                return True, f"Note ID {note_data.id} had no content and was removed from index.", doc_id_to_check
            else:
                return False, f"Note ID {note_data.id} had no content but failed to be removed from index.", doc_id_to_check
        return False, msg, doc_id_to_check

    llama_doc = db_note_to_llama_document(note_data)
    doc_id = llama_doc.doc_id

    success = refresh_document_in_index(index, llama_doc)  # This uses index.refresh_ref_docs

    if success:
        persist_index_and_vector_store(index, vector_store)
        msg = f"Index service: Note ID {note_data.id} (doc_id: {doc_id}) processed (added/updated) in index."
        logger.info(msg)
        return True, msg, doc_id
    else:
        msg = f"Index service: Failed to process (add/update) note ID {note_data.id} (doc_id: {doc_id}) in index."
        logger.error(msg)
        return False, msg, doc_id


def get_index_statistics() -> Tuple[int, str]:
    index = get_global_vector_index()
    vector_store = get_global_faiss_vector_store()

    if not index or not vector_store or not hasattr(vector_store, '_faiss_index') or not vector_store._faiss_index:
        logger.info("Index service stats: globals not found, attempting to initialize/load index...")
        index, vector_store = _get_active_index_and_store()
        if not index or not vector_store or not vector_store._faiss_index:
            return 0, "Index service: Index or FAISS store not fully initialized or available."
    try:
        num_vectors = vector_store._faiss_index.ntotal
        num_docs_in_docstore = len(index.docstore.docs) if index.docstore else 0
        faiss_type_str = get_faiss_index_type_description(vector_store)

        message = (f"FAISS Vectors: {num_vectors}. Docs in Docstore: {num_docs_in_docstore}. "
                   f"Current FAISS Index Type: {faiss_type_str}.")
        return num_vectors, message
    except Exception as e:
        logger.exception("Index service: Error retrieving index stats.");
        return 0, f"Error getting stats: {str(e)}"