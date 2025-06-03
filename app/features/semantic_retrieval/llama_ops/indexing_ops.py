# app/features/semantic_retrieval/llama_ops/indexing_ops.py
import logging
from typing import List, Optional
import numpy as np

from llama_index.core import VectorStoreIndex, Document as LlamaDocument

logger = logging.getLogger(__name__)


def refresh_document_in_index(
        index: VectorStoreIndex,
        llama_doc: LlamaDocument,
        show_progress: bool = False
) -> bool:
    """
    Refreshes (adds/updates) a single LlamaDocument in the given index.
    LlamaIndex's refresh_ref_docs should handle deletion of old versions
    and insertion of new ones, leveraging FaissVectorStore's delete and add
    which in turn should use IndexIDMap's remove_ids and add_with_ids.
    Returns True if successful, False otherwise.
    """
    try:
        logger.debug(f"Llama_ops: Refreshing document ID {llama_doc.doc_id} in index.")
        # refresh_ref_docs expects a list
        refreshed_doc_ids = index.refresh_ref_docs([llama_doc], show_progress=show_progress)
        if llama_doc.doc_id in refreshed_doc_ids:
            logger.info(f"Llama_ops: Successfully refreshed document ID {llama_doc.doc_id} in index.")
            return True
        else:
            logger.warning(
                f"Llama_ops: Document ID {llama_doc.doc_id} not in refreshed_doc_ids list after refresh. {refreshed_doc_ids}")
            # This might happen if the document was purely new and not an update of an existing one.
            # Check if it exists in docstore now.
            if index.docstore.document_exists(llama_doc.doc_id):
                logger.info(
                    f"Llama_ops: Document ID {llama_doc.doc_id} confirmed in docstore post-refresh (likely new).")
                return True
            logger.error(f"Llama_ops: Failed to confirm refresh/addition of document ID {llama_doc.doc_id}.")
            return False
    except Exception as e:
        logger.error(f"Llama_ops: Error refreshing document ID {llama_doc.doc_id} in index: {e}", exc_info=True)
        return False


def remove_document_from_index(
        index: VectorStoreIndex,
        doc_id_to_delete: str
) -> bool:
    """
    Removes a document (and its vectors via IndexIDMap) from the index and DocStore.
    Returns True if successful or if document was not found (idempotent), False on error.
    """
    logger.debug(f"Llama_ops: Attempting to remove doc_id: {doc_id_to_delete} from index and DocStore.")

    if not index.docstore.document_exists(doc_id_to_delete):
        logger.info(f"Llama_ops: Doc_id: {doc_id_to_delete} not found in DocStore. Considered successfully removed.")
        return True

    try:
        # This should call FaissVectorStore.delete_ref_doc -> _faiss_index.remove_ids
        index.delete_ref_doc(doc_id_to_delete, delete_from_docstore=True)

        # Verify deletion from DocStore
        if index.docstore.document_exists(doc_id_to_delete):
            logger.error(f"Llama_ops: Doc_id: {doc_id_to_delete} still exists in DocStore after delete_ref_doc call.")
            # Attempt manual docstore deletion if necessary, though delete_ref_doc should handle it
            try:
                index.docstore.delete_document(doc_id_to_delete, raise_error=False)
                if index.docstore.document_exists(doc_id_to_delete):
                    logger.error(f"Llama_ops: Manual DocStore deletion also failed for {doc_id_to_delete}.")
                    return False  # Indicate failure if docstore removal failed
            except Exception as ds_e:
                logger.error(f"Llama_ops: Error during manual DocStore deletion for {doc_id_to_delete}: {ds_e}")
                return False

        logger.info(f"Llama_ops: Doc_id: {doc_id_to_delete} removed from index (vectors via IndexIDMap) and DocStore.")
        return True
    except NotImplementedError:
        logger.error(
            "Llama_ops: delete_ref_doc or underlying vector deletion is not implemented for the current VectorStore. "
            "Physical vector deletion with IndexIDMap failed."
        )
        return False
    except Exception as e:
        logger.error(f"Llama_ops: Error removing doc_id {doc_id_to_delete} from index: {e}", exc_info=True)
        return False