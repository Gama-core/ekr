import logging
from llama_index.core import VectorStoreIndex, Document as LlamaDocument

logger = logging.getLogger(__name__)

def refresh_document_in_index(index: VectorStoreIndex, llama_doc: LlamaDocument, show_progress: bool = False) -> bool:
    try:
        index.refresh_ref_docs([llama_doc], show_progress=show_progress)
        logger.info(f"Document {llama_doc.id_} successfully refreshed in index.")
        return True
    except Exception as e:
        logger.exception(f"Error refreshing document {llama_doc.id_}: {e}")
        return False

def remove_document_from_index(index: VectorStoreIndex, doc_id_to_delete: str) -> bool:
    logger.debug(f"Attempting to remove doc_id: {doc_id_to_delete}")
    if not index.docstore.document_exists(doc_id_to_delete):
        logger.info(f"Doc_id: {doc_id_to_delete} not found in DocStore. No action needed.")
        return True
    try:
        index.delete_ref_doc(doc_id_to_delete, delete_from_docstore=True)
        if not index.docstore.document_exists(doc_id_to_delete):
            logger.info(f"Doc_id: {doc_id_to_delete} successfully removed.")
            return True
        else:
            logger.error(f"Doc_id: {doc_id_to_delete} still exists in DocStore after deletion attempt.")
            return False
    except Exception as e:
        logger.error(f"Error removing doc_id {doc_id_to_delete}: {e}", exc_info=True)
        return False