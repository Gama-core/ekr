# app/schemas/assistant.py
from pydantic import BaseModel, Field
from typing import List, Optional, Literal, Union
# from app.schemas.agent import AgentStep # Optional for debugging

class AssistantQueryRequest(BaseModel):
    """
    Request schema for the assistant query endpoint.
    """
    user_query: str = Field(..., description="The user's original question or prompt.")
    # Renamed flag for clarity:
    use_semantic_search: bool = Field(default=False, description="Flag to enable searching the knowledge base using semantic search (RAG). Default is False as RAG is not yet implemented.")
    use_web_search: bool = Field(default=False, description="Flag to enable real-time web search and crawling for context.")
    selected_note_ids: Optional[List[int]] = Field(None, description="List of specific Note IDs to use as additional context.")
    conversation_id: Optional[str] = Field(None, description="Identifier for the ongoing conversation, for context management.")

    model_config = { # Pydantic v2 config example
        "json_schema_extra": {
            "examples": [
                {
                    "user_query": "What were the key findings of the latest climate change report?",
                    "use_semantic_search": False, # Example: Relying on web search
                    "use_web_search": True,
                    "selected_note_ids": None,
                },
                {
                    "user_query": "Summarize the main points from my notes on Project Alpha.",
                    "use_semantic_search": False, # Example: Only using selected notes
                    "use_web_search": False,
                    "selected_note_ids": [101, 105, 123],
                },
                 {
                    "user_query": "Compare Project Alpha with latest industry trends.",
                    "use_semantic_search": True, # Example: Use RAG (when implemented) + web
                    "use_web_search": True,
                    "selected_note_ids": [101], # Optionally also include specific notes
                }
            ]
        }
    }

# --- Source and AssistantResponse remain the same ---
class Source(BaseModel):
    """
    Schema representing a source of information used for the answer.
    """
    type: Literal["note", "document", "web"] = Field(..., description="The type of the source (internal note, internal document, or external web page).")
    id: Optional[Union[int, str]] = Field(None, description="The internal ID (for note/document) or potentially a unique identifier.")
    title: Optional[str] = Field(None, description="The title of the note or web page.")
    url: Optional[str] = Field(None, description="The URL, primarily for web sources.")
    relevance_score: Optional[float] = Field(None, description="Score indicating relevance, typically from RAG.")

class AssistantResponse(BaseModel):
    """
    Response schema for the assistant query endpoint.
    """
    answer: str = Field(..., description="The synthesized answer to the user's query.")
    sources: List[Source] = Field([], description="List of sources used to generate the answer.")
    conversation_id: Optional[str] = Field(None, description="Identifier for the ongoing conversation.")
    # Optional: Reuse AgentStep for debugging/transparency if needed
    # intermediate_steps: List[AgentStep] = []