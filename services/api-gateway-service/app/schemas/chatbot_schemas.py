# app/schemas/chatbot_schemas.py
from pydantic import BaseModel, Field
from typing import Optional, List, Literal

class ChatMessage(BaseModel):
    """Represents a single message in the conversation history."""
    role: Literal["user", "assistant"]
    content: str

class ChatRequest(BaseModel):
    """The request model for a new chat message."""
    query: str
    history: List[ChatMessage] = []
    # For now, we assume a hardcoded user_id, but in a real app,
    # this would come from an auth token. We'll add it here for the service layer.
    user_id: int = 1
    web_search_enabled: bool = False

class Source(BaseModel):
    """Represents a source document used to generate an answer."""
    type: Literal["note", "file"]
    title: str
    note_id: Optional[int] = None
    content_snippet: str

class ChatResponse(BaseModel):
    """The response model for a chat message."""
    answer: str
    sources: List[Source] = []

class FileData(BaseModel):
    """A simple structure to hold a file's data after being read."""
    filename: str
    content_type: Optional[str]
    content_bytes: bytes