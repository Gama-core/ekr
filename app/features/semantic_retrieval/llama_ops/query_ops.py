# app/features/semantic_retrieval/llama_ops/query_ops.py
import logging
from typing import List, Optional, Tuple

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore

from app.features.semantic_retrieval.schemas import RetrievedContextItem
from app.features.semantic_retrieval.config import semantic_retrieval_config

logger = logging.getLogger(__name__)


async def execute_query_against_index(
        index: VectorStoreIndex,
        query_text: str,
        user_id: int,
        top_k_override: Optional[int] = None
) -> Tuple[List[RetrievedContextItem], str]:
    actual_top_k_final = top_k_override or semantic_retrieval_config.DEFAULT_SIMILARITY_TOP_K
    candidate_fetch_factor = 10
    internal_retrieval_k = actual_top_k_final * candidate_fetch_factor
    internal_retrieval_k = min(internal_retrieval_k, 100)

    logger.info(
        f"Llama_ops: Retrieving top {actual_top_k_final} (internal k: {internal_retrieval_k}) "
        f"for user {user_id}, query: '{query_text[:50]}...'"
    )

    if not index or not index.docstore:
        err_msg = "Llama_ops: Vector index or DocStore not available for retrieval."
        logger.error(err_msg)
        return [], err_msg

    try:
        retriever = index.as_retriever(similarity_top_k=internal_retrieval_k)
        all_candidate_nodes_with_scores: List[NodeWithScore] = await retriever.aretrieve(query_text)

        valid_user_items: List[RetrievedContextItem] = []
        if all_candidate_nodes_with_scores:
            logger.debug(
                f"Llama_ops: Retrieved {len(all_candidate_nodes_with_scores)} global candidates. Filtering...")

            for node_with_score in all_candidate_nodes_with_scores:
                node = node_with_score.node
                doc_id = node.node_id or node.id_

                if not index.docstore.document_exists(doc_id):  # Check DocStore
                    logger.debug(f"Llama_ops: Node {doc_id} not in DocStore, skipping.")
                    continue

                metadata = node.metadata or {}
                node_owner_id_str = metadata.get("owner_id")
                if node_owner_id_str != str(user_id):
                    continue

                raw_note_id = metadata.get("note_id")
                note_id_val: Optional[int] = None
                if raw_note_id:
                    try:
                        note_id_val = int(raw_note_id)
                    except ValueError:
                        logger.warning(f"Llama_ops: Bad note_id '{raw_note_id}' in metadata for node {doc_id}.")

                item = RetrievedContextItem(
                    note_id=note_id_val,
                    doc_id=doc_id,
                    title=metadata.get("title", "Untitled"),
                    text_chunk=node.get_content(),
                    score=round(node_with_score.score, 4) if node_with_score.score is not None else None,
                    metadata=metadata
                )
                valid_user_items.append(item)

            valid_user_items.sort(key=lambda x: x.score if x.score is not None else float('inf'))
            final_items_for_user = valid_user_items[:actual_top_k_final]

            message = f"Successfully retrieved {len(final_items_for_user)} context items for user {user_id}."
            if not final_items_for_user and valid_user_items:  # Found items but not for this k after sort
                message = f"Found {len(valid_user_items)} items for user {user_id} but 0 for top_k {actual_top_k_final}."
            elif not final_items_for_user and all_candidate_nodes_with_scores:
                message = f"No context items found for user {user_id} after filtering {len(all_candidate_nodes_with_scores)} global candidates."
            elif not all_candidate_nodes_with_scores:
                message = f"No relevant context items found globally for query by user {user_id}."

            logger.info(f"Llama_ops: {message}")
            return final_items_for_user, message
        else:
            msg = f"Llama_ops: No relevant items found globally for query: '{query_text[:50]}...'"
            logger.info(msg)
            return [], msg

    except Exception as e:
        error_msg = f"Llama_ops: Error during context retrieval for user {user_id}: {type(e).__name__} - {str(e)}"
        logger.exception(error_msg)
        return [], error_msg