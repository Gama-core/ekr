# app/features/semantic_retrieval/retrieval_service.py
import logging
from typing import List, Optional, Tuple

# from llama_index.core.response.schema import StreamingResponse  # For potential streaming later

# Feature specific imports
from app.features.semantic_retrieval.index_service import get_vector_index
from app.features.semantic_retrieval.schemas import RetrievedContextItem
from app.features.semantic_retrieval.config import semantic_retrieval_config

# LLM Query service if synthesis is done here (but we decided against it for now)
# from app.features.llm_query.llm_service import generate_llm_response

logger = logging.getLogger(__name__)


async def retrieve_relevant_context(
        query_text: str,
        top_k_override: Optional[int] = None
) -> Tuple[List[RetrievedContextItem], Optional[str]]:
    """
    Retrieves semantically relevant context items from the indexed knowledge.
    Returns a list of context items and an optional message.
    """
    actual_top_k = top_k_override or semantic_retrieval_config.DEFAULT_SIMILARITY_TOP_K
    logger.info(f"Retrieving top {actual_top_k} relevant contexts for query: '{query_text[:100]}...'")

    try:
        vector_index = get_vector_index()  # Ensures index is loaded and settings are initialized
        if not vector_index:
            err_msg = "Vector index is not available for retrieval."
            logger.error(err_msg)
            return [], err_msg

        # Using retriever for more direct access to nodes and scores
        retriever = vector_index.as_retriever(similarity_top_k=actual_top_k)
        retrieved_nodes_with_scores = await retriever.aretrieve(query_text)  # Async retrieval

        retrieved_items: List[RetrievedContextItem] = []
        if retrieved_nodes_with_scores:
            logger.info(f"Retrieved {len(retrieved_nodes_with_scores)} nodes with scores.")
            for node_with_score in retrieved_nodes_with_scores:
                node = node_with_score.node
                metadata = node.metadata or {}

                # Safely get note_id and convert to int if possible
                raw_note_id = metadata.get("note_id")
                note_id_val: Optional[int] = None
                if raw_note_id:
                    try:
                        note_id_val = int(raw_note_id)
                    except ValueError:
                        logger.warning(f"Could not convert note_id '{raw_note_id}' to int for node {node.node_id}.")

                item = RetrievedContextItem(
                    note_id=note_id_val,
                    doc_id=node.node_id or node.id_,  # node.id_ is an alias for node_id
                    title=metadata.get("title", "Untitled"),
                    text_chunk=node.get_content(),
                    score=round(node_with_score.score, 4) if node_with_score.score is not None else None,
                    metadata=metadata
                )
                retrieved_items.append(item)
                logger.debug(
                    f"  -> Retrieved chunk: Note ID {item.note_id}, Doc ID {item.doc_id}, "
                    f"Score: {item.score}, Title: '{item.title[:50]}...'"
                )
            return retrieved_items, f"Successfully retrieved {len(retrieved_items)} context items."
        else:
            logger.info(f"No relevant context items found for query: '{query_text[:100]}...'")
            return [], "No relevant context items found."

    except Exception as e:
        error_msg = f"Error during context retrieval: {type(e).__name__} - {str(e)}"
        logger.exception(error_msg)
        return [], error_msg