import logging
from typing import List, Optional, Tuple, cast

from llama_index.core import Document as LlamaDocument, VectorStoreIndex, Settings as LlamaSettings

from .config import settings
from .clients import database_client
from .schemas import NoteForIndex
from .llama_ops import (
    db_note_to_llama_document,
    ensure_vector_index,
    persist_index_and_vector_store,
    clear_index_storage_completely,
    refresh_document_in_index,
    remove_document_from_index,
    get_global_faiss_vector_store,
    get_faiss_index_type_description
)
from .llama_ops.custom_faiss_vstore import CustomFaissVectorStore

logger = logging.getLogger(__name__)


def _get_active_index_and_store() -> Tuple[Optional[VectorStoreIndex], Optional[CustomFaissVectorStore]]:
    index = ensure_vector_index()
    vector_store = get_global_faiss_vector_store()
    if not index or not vector_store or not vector_store._faiss_index:
        logger.error("Index service: Index or FAISS vector store unavailable.")
        return None, None
    return index, cast(CustomFaissVectorStore, vector_store)


async def build_full_index(force_rebuild: bool = False) -> Tuple[int, int]:
    logger.info(f"Index service: Full index build started. Force rebuild: {force_rebuild}")
    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store: return 0, 0

    if not force_rebuild and len(index.docstore.docs) > 0:
        logger.info("Index already populated and force_rebuild=False. Skipping full build.")
        return 0, vector_store._faiss_index.ntotal

    if force_rebuild:
        clear_index_storage_completely()
        index, vector_store = _get_active_index_and_store()
        if not index or not vector_store: return 0, 0

    logger.info("Fetching all notes from database-api via client...")
    notes_processed, all_llama_docs = 0, []
    async for note in database_client.stream_all_notes():
        if note.text_content and note.text_content.strip():
            all_llama_docs.append(db_note_to_llama_document(note))
        notes_processed += 1
        if notes_processed >= settings.MAX_NOTES_FOR_INITIAL_BUILD:
            logger.warning(f"Reached MAX_NOTES_FOR_INITIAL_BUILD limit of {settings.MAX_NOTES_FOR_INITIAL_BUILD}.")
            break

    if not all_llama_docs:
        logger.warning("No processable notes found from database-api.")
        return 0, 0

    logger.info(f"Populating index with {len(all_llama_docs)} documents from {notes_processed} notes.")
    index.insert_nodes(all_llama_docs, show_progress=True)

    final_vectors = vector_store._faiss_index.ntotal
    persist_index_and_vector_store(index, vector_store)
    logger.info(f"Index build complete. Total vectors in FAISS: {final_vectors}.")
    return notes_processed, final_vectors


def add_or_update_note_in_index(note_data: NoteForIndex) -> Tuple[bool, str, Optional[str]]:
    logger.info(f"Adding/updating note ID {note_data.id} in index.")
    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store: return False, "Index/vector store not available.", None

    llama_doc, doc_id = db_note_to_llama_document(note_data), f"note_{note_data.id}"
    success = refresh_document_in_index(index, llama_doc)
    if success:
        persist_index_and_vector_store(index, vector_store)
        return True, f"Note ID {doc_id} processed successfully.", doc_id
    else:
        return False, f"Failed to process note ID {doc_id}.", doc_id


def delete_note_from_index(note_id: int) -> Tuple[bool, str, Optional[str]]:
    doc_id = f"note_{note_id}"
    logger.info(f"Attempting to delete doc_id {doc_id} from index.")
    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store: return False, "Index/vector store not available.", doc_id

    success = remove_document_from_index(index, doc_id)
    if success:
        persist_index_and_vector_store(index, vector_store)
        return True, f"Successfully processed deletion for doc_id {doc_id}.", doc_id
    else:
        return False, f"Failed to delete doc_id {doc_id}.", doc_id


def get_index_statistics() -> dict:
    index, vector_store = _get_active_index_and_store()
    if not index or not vector_store or not vector_store._faiss_index:
        return {"message": "Index or FAISS store not fully initialized."}

    return {
        "total_indexed_vectors": vector_store._faiss_index.ntotal,
        "num_docs_in_docstore": len(index.docstore.docs),
        "faiss_index_type": get_faiss_index_type_description(vector_store),
        "faiss_index_dimension": vector_store._faiss_index.d,
        "llama_configured_chunk_size": LlamaSettings.chunk_size,
        "llama_configured_chunk_overlap": LlamaSettings.chunk_overlap,
        "llama_embedding_model_name": getattr(LlamaSettings.embed_model, 'model_name', 'N/A'),
        "index_storage_path": str(settings.VECTOR_STORE_PATH.resolve()),
        "message": "Index statistics retrieved successfully."
    }