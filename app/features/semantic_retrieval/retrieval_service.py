# app/features/semantic_retrieval/retrieval_service.py
import logging
from typing import List, Optional, Tuple  # Ensure Tuple is imported

from app.features.semantic_retrieval.index_service import get_vector_index
from app.features.semantic_retrieval.schemas import RetrievedContextItem
from app.features.semantic_retrieval.config import semantic_retrieval_config

logger = logging.getLogger(__name__)


async def retrieve_relevant_context(
        query_text: str,
        user_id: int,
        top_k_override: Optional[int] = None
) -> Tuple[List[RetrievedContextItem], Optional[str]]:  # <--- Corrected: No spaces inside List[]
    """
    Retrieves semantically relevant context items, filters for the specified user,
    and filters out logically deleted items by checking DocStore.
    Scores are assumed to be distances (lower is better) if IndexFlatL2 is used.
    """
    actual_top_k_final = top_k_override or semantic_retrieval_config.DEFAULT_SIMILARITY_TOP_K
    candidate_fetch_factor = 10
    internal_retrieval_k = actual_top_k_final * candidate_fetch_factor
    internal_retrieval_k = min(internal_retrieval_k, 100)

    logger.info(
        f"Retrieving top {actual_top_k_final} (internal k: {internal_retrieval_k}) "
        f"for user {user_id}, query: '{query_text[:50]}...'"
    )

    try:
        vector_index = get_vector_index()
        if not vector_index or not vector_index.docstore:
            err_msg = "Vector index or DocStore not available for retrieval."
            logger.error(err_msg)
            return [], err_msg

        retriever = vector_index.as_retriever(
            similarity_top_k=internal_retrieval_k,
        )
        all_candidate_nodes_with_scores = await retriever.aretrieve(query_text)

        valid_user_items: List[RetrievedContextItem] = []
        if all_candidate_nodes_with_scores:
            logger.debug(
                f"Retrieved {len(all_candidate_nodes_with_scores)} global candidates. Filtering and sorting...")

            for node_with_score in all_candidate_nodes_with_scores:
                node = node_with_score.node
                doc_id = node.node_id or node.id_

                if not vector_index.docstore.document_exists(doc_id):
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
                        logger.warning(f"Bad note_id '{raw_note_id}' in metadata for node {node.node_id}.")

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

            if final_items_for_user:
                top_scores_log = [item.score for item in final_items_for_user]
                logger.info(
                    f"Top {len(final_items_for_user)} scores after sorting (ascending for distance): {top_scores_log}")

            logger.info(
                f"Found {len(valid_user_items)} valid items for user {user_id} post-filter. Returning top {len(final_items_for_user)}.")
            return final_items_for_user, f"Successfully retrieved {len(final_items_for_user)} context items for user {user_id}."
        else:
            logger.info(f"No relevant items found globally for query: '{query_text[:50]}...'")
            return [], f"No relevant context items found for user {user_id} (no global matches)."

    except Exception as e:
        error_msg = f"Error during context retrieval for user {user_id}: {type(e).__name__} - {str(e)}"
        logger.exception(error_msg)
        return [], error_msg