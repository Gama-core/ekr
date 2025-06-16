import logging
from typing import List, Optional, Tuple

from llama_index.core import VectorStoreIndex
from llama_index.core.schema import NodeWithScore

from ..schemas import RetrievedContextItem
from ..config import settings

logger = logging.getLogger(__name__)


async def execute_query_against_index(
        index: VectorStoreIndex,
        query_text: str,
        user_id: int,
        top_k_override: Optional[int] = None
) -> Tuple[List[RetrievedContextItem], str]:
    actual_top_k = top_k_override or settings.DEFAULT_SIMILARITY_TOP_K

    logger.info(f"Llama_ops: Retrieving top {actual_top_k} for user {user_id}.")

    if not index or not index.vector_store:
        err_msg = "Llama_ops: Vector index or VectorStore not available for retrieval."
        logger.error(err_msg)
        return [], err_msg

    try:
        retriever = index.as_retriever(similarity_top_k=actual_top_k * 5)  # Fetch more to filter
        all_nodes: List[NodeWithScore] = await retriever.aretrieve(query_text)

        valid_user_items: List[RetrievedContextItem] = []
        for node_with_score in all_nodes:
            if str(node_with_score.node.metadata.get("owner_id")) == str(user_id):
                item = RetrievedContextItem(
                    note_id=int(node_with_score.node.metadata.get("note_id", 0)),
                    doc_id=node_with_score.node.node_id,
                    title=node_with_score.node.metadata.get("title", "Untitled"),
                    text_chunk=node_with_score.node.get_content(),
                    score=round(node_with_score.score, 4) if node_with_score.score is not None else None,
                    metadata=node_with_score.node.metadata
                )
                valid_user_items.append(item)

        final_items = sorted(valid_user_items, key=lambda x: x.score or float('inf'))[:actual_top_k]

        message = f"Successfully retrieved {len(final_items)} context items for user {user_id}."
        logger.info(message)
        return final_items, message

    except Exception as e:
        error_msg = f"Llama_ops: Error during context retrieval for user {user_id}: {e}"
        logger.exception(error_msg)
        return [], error_msg