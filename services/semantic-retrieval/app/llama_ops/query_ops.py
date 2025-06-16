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

    if not index or not index.docstore or not index.vector_store:
        err_msg = "Llama_ops: Vector index, DocStore, or VectorStore not available for retrieval."
        logger.error(err_msg)
        return [], err_msg

    try:
        retriever = index.as_retriever(similarity_top_k=internal_retrieval_k)
        all_candidate_nodes_with_scores: List[NodeWithScore] = await retriever.aretrieve(query_text)

        logger.info(
            f"Llama_ops: Retriever returned {len(all_candidate_nodes_with_scores)} candidate NodeWithScore objects.")
        if all_candidate_nodes_with_scores:
            logger.info(
                f"Llama_ops: First candidate node ID from retriever: {all_candidate_nodes_with_scores[0].node.node_id}, Score: {all_candidate_nodes_with_scores[0].score}")
        else:
            logger.info("Llama_ops: Retriever returned no candidate nodes.")
            # ADDED DEBUG BLOCK
            if hasattr(index, 'index_struct') and hasattr(index.index_struct, 'nodes_dict'):  # type: ignore
                nodes_dict_keys = list(index.index_struct.nodes_dict.keys())  # type: ignore
                logger.warning(
                    f"Llama_ops: DEBUG - Retriever found 0 nodes. Current keys in index.index_struct.nodes_dict (sample of up to 20): {nodes_dict_keys[:20]}")
                if not nodes_dict_keys:
                    logger.warning("Llama_ops: DEBUG - index.index_struct.nodes_dict is EMPTY.")
            else:
                logger.warning(
                    "Llama_ops: DEBUG - index.index_struct or index.index_struct.nodes_dict not found for inspection.")

            if hasattr(index, 'docstore'):
                docstore_keys = list(index.docstore.docs.keys())
                logger.warning(
                    f"Llama_ops: DEBUG - Current docs in index.docstore (sample IDs of up to 20): {docstore_keys[:20]}")
                if not docstore_keys:
                    logger.warning("Llama_ops: DEBUG - index.docstore.docs is EMPTY.")

        valid_user_items: List[RetrievedContextItem] = []
        if all_candidate_nodes_with_scores:
            logger.debug(
                f"Llama_ops: Filtering {len(all_candidate_nodes_with_scores)} global candidates from retriever...")

            for node_with_score in all_candidate_nodes_with_scores:
                node = node_with_score.node
                doc_id_str = node.node_id or node.id_
                logger.info(f"Llama_ops: Processing candidate node '{doc_id_str}' with score {node_with_score.score}")

                if not index.docstore.document_exists(doc_id_str):
                    logger.warning(
                        f"Llama_ops: Node '{doc_id_str}' (string ID from retriever) NOT IN DOCSTORE. Skipping.")
                    continue

                metadata = node.metadata or {}
                node_owner_id_str = metadata.get("owner_id")
                logger.info(
                    f"Llama_ops: Node '{doc_id_str}' metadata owner_id: '{node_owner_id_str}', query user_id: '{user_id}'")
                if node_owner_id_str != str(user_id):
                    logger.info(f"Llama_ops: Node '{doc_id_str}' owner_id mismatch. Skipping user {user_id}.")
                    continue

                raw_note_id = metadata.get("note_id")
                note_id_val: Optional[int] = None
                if raw_note_id:
                    try:
                        note_id_val = int(raw_note_id)
                    except ValueError:
                        logger.warning(f"Llama_ops: Bad note_id '{raw_note_id}' in metadata for node {doc_id_str}.")

                item = RetrievedContextItem(
                    note_id=note_id_val,
                    doc_id=doc_id_str,
                    title=metadata.get("title", "Untitled"),
                    text_chunk=node.get_content(),
                    score=round(node_with_score.score, 4) if node_with_score.score is not None else None,
                    metadata=metadata
                )
                valid_user_items.append(item)
                logger.debug(f"Llama_ops: Node '{doc_id_str}' is valid for user {user_id}. Added to results.")

            # sort so the smallest distance (best match) is first
            valid_user_items.sort(
                     key = lambda x: x.score if x.score is not None else float("inf")
            )
            final_items_for_user = valid_user_items[:actual_top_k_final]

            message = f"Successfully retrieved {len(final_items_for_user)} context items for user {user_id} out of {len(valid_user_items)} valid after filtering."
            if not final_items_for_user and valid_user_items:
                message = f"Found {len(valid_user_items)} items for user {user_id} but 0 for top_k {actual_top_k_final} after sorting/slicing."
            elif not final_items_for_user and all_candidate_nodes_with_scores:
                message = f"No context items found for user {user_id} after filtering {len(all_candidate_nodes_with_scores)} global candidates."
            elif not all_candidate_nodes_with_scores:
                message = f"No relevant context items found globally for query by user {user_id} (retriever found 0 candidates)."

            logger.info(f"Llama_ops: {message}")
            return final_items_for_user, message
        else:
            msg = f"Llama_ops: No relevant candidate nodes found globally by retriever for query: '{query_text[:50]}...'"
            logger.info(msg)
            return [], msg

    except Exception as e:
        error_msg = f"Llama_ops: Error during context retrieval for user {user_id}: {type(e).__name__} - {str(e)}"
        logger.exception(error_msg)
        return [], error_msg