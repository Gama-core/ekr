import logging
from typing import List, Optional, Tuple

from .schemas import RetrievedContextItem
from .llama_ops import get_active_vector_index, execute_query_against_index

logger = logging.getLogger(__name__)

async def retrieve_relevant_context(
    query_text: str, user_id: int, top_k_override: Optional[int] = None
) -> Tuple[List[RetrievedContextItem], Optional[str]]:
    logger.info(f"Retrieval service: request for user_id: {user_id}, query: '{query_text[:50]}...'")
    vector_index = get_active_vector_index()
    if not vector_index:
        err_msg = "Retrieval service: Vector index is not available."
        logger.error(err_msg)
        return [], err_msg
    try:
        items, message = await execute_query_against_index(
            index=vector_index,
            query_text=query_text,
            user_id=user_id,
            top_k_override=top_k_override
        )
        return items, message
    except Exception as e:
        error_msg = f"Retrieval error for user {user_id}: {type(e).__name__} - {e}"
        logger.exception(error_msg)
        return [], error_msg