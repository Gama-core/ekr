# app/schemas/ai_assistant_schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class ChatMessage(BaseModel):
    """Represents a single message in the conversation history."""
    role: Literal["user", "assistant"]
    content: str

class AIAssistantRequest(BaseModel):
    """The request model for asking the AI assistant a question."""
    question: str = Field(..., description="The user's new question for the AI assistant.")
    note_context: str = Field(..., description="The full text content of the currently active note.")
    history: List[ChatMessage] = Field([], description="The history of the conversation so far.")

class AIAssistantResponse(BaseModel):
    """The response model for the AI assistant's answer."""
    answer: str
    model_used: Optional[str] = None