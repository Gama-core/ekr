# app/features/semantic_retrieval/llama_ops/indexing_ops.py
import logging
from typing import List, Optional
import numpy as np

from llama_index.core import VectorStoreIndex, Document as LlamaDocument

logger = logging.getLogger(__name__)

def refresh_document_in_index(index: VectorStoreIndex,
                                  llama_doc: LlamaDocument,
                                  show_progress: bool = False) -> bool:
        try:
            if index.docstore.document_exists(llama_doc.id_):
                index.refresh_ref_docs([llama_doc], show_progress=show_progress)
            else:
                index.insert_nodes([llama_doc])

            if index.docstore.document_exists(llama_doc.id_):
                logger.info("Document %s successfully (re)indexed", llama_doc.id_)
                return True

            logger.error("Document %s still missing after insert/refresh", llama_doc.id_)
            return False
        except Exception as e:
            logger.exception("Error (re)indexing %s: %s", llama_doc.id_, e)
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


def remove_document_from_index(
        index: VectorStoreIndex,
        doc_id_to_delete: str
) -> bool:
    """
    Removes a document (and its vectors via IndexIDMap/IndexIDMap2) from the index and DocStore.
    Returns True if successful or if document was not found (idempotent), False on error.
    """
    logger.debug(f"Llama_ops: Attempting to remove doc_id: {doc_id_to_delete} from index and DocStore.")

    if not index.docstore.document_exists(doc_id_to_delete):
        logger.info(f"Llama_ops: Doc_id: {doc_id_to_delete} not found in DocStore. Considered successfully removed.")
        return True

    try:
        # This should call FaissVectorStore.delete -> _faiss_index.remove_ids (for IndexIDMap/IndexIDMap2)
        index.delete_ref_doc(doc_id_to_delete, delete_from_docstore=True)

        # Verify deletion from DocStore
        if index.docstore.document_exists(doc_id_to_delete):
            logger.error(f"Llama_ops: Doc_id: {doc_id_to_delete} still exists in DocStore after delete_ref_doc call.")
            # Attempt manual docstore deletion if necessary
            try:
                index.docstore.delete_document(doc_id_to_delete, raise_error=False)
                if index.docstore.document_exists(doc_id_to_delete):
                    logger.error(f"Llama_ops: Manual DocStore deletion also failed for {doc_id_to_delete}.")
                    return False
            except Exception as ds_e:
                logger.error(f"Llama_ops: Error during manual DocStore deletion for {doc_id_to_delete}: {ds_e}")
                return False

        logger.info(f"Llama_ops: Doc_id: {doc_id_to_delete} likely removed from index (vectors via IndexIDMap2) and DocStore.")
        return True
    except NotImplementedError: # Should not happen with FaissVectorStore
        logger.error(
            "Llama_ops: delete_ref_doc or underlying vector deletion is not implemented for the current VectorStore. "
            "Physical vector deletion with IndexIDMap2 failed."
        )
        return False
    except Exception as e:
        logger.error(f"Llama_ops: Error removing doc_id {doc_id_to_delete} from index: {e}", exc_info=True)
        return False