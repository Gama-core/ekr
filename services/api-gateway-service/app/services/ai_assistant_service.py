# app/services/ai_assistant_service.py
import logging
from typing import List
from .. import clients
from ..schemas import ai_assistant_schemas

logger = logging.getLogger(__name__)


async def get_assistant_response(
        question: str,
        note_context: str,
        history: List[ai_assistant_schemas.ChatMessage]
) -> ai_assistant_schemas.AIAssistantResponse:
    """
    Orchestrates getting a response from the LLM based on note context and conversation history.
    """
    logger.info(f"Orchestrating AI Assistant request with {len(history)} history messages.")

    # Step 1: Define the system prompt. This tells the AI its persona.
    system_prompt = (
        "You are a helpful AI assistant integrated into a note-taking application. "
        "Your primary task is to answer the user's questions based *only* on the document context provided. "
        "You should also consider the previous conversation history for context. "
        "Do not use any external knowledge. If the answer is not in the context or history, say so clearly. "
        "Be concise and directly answer the question."
    )

    # Step 2: Flatten the conversation history and context into a single user_prompt string.
    # This is the format that the llm-query-service currently expects.
    prompt_parts = []
    prompt_parts.append(
        "Based on the following document context and conversation history, please answer my new question.\n\n"
        "--- DOCUMENT CONTEXT ---\n"
        f"{note_context}\n"
        "--- END OF CONTEXT ---"
    )

    if history:
        prompt_parts.append("\n--- CONVERSATION HISTORY ---")
        for message in history:
            # Format history clearly for the LLM
            prompt_parts.append(f"{message.role.capitalize()}: {message.content}")
        prompt_parts.append("--- END OF HISTORY ---")

    prompt_parts.append(f"\nNew Question: {question}")

    user_prompt = "\n".join(prompt_parts)

    # Step 3: Construct the payload in the format the llm-query-service expects.
    llm_payload = {
        "user_prompt": user_prompt,
        "system_prompt": system_prompt,
    }

    # Step 4: Call the llm-query service.
    llm_response_data = await clients.llm_query_client.query_llm(llm_payload)

    # Step 5: Format and return the response.
    return ai_assistant_schemas.AIAssistantResponse(
        answer=llm_response_data.get("response_text", "No response from model.").strip(),
        model_used=llm_response_data.get("model_used")
    )