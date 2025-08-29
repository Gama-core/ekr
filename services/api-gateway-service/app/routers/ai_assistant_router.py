# app/routers/ai_assistant_router.py
import logging
from fastapi import APIRouter

from ..services import ai_assistant_service
from ..schemas import ai_assistant_schemas

logger = logging.getLogger(__name__)
router = APIRouter(
    prefix="/assistant",
    tags=["AI Assistant"]
)

@router.post("/ask", response_model=ai_assistant_schemas.AIAssistantResponse)
async def ask_assistant(request: ai_assistant_schemas.AIAssistantRequest):
    """
    Sends a question, conversation history, and a note's context to the AI Assistant.
    """
    return await ai_assistant_service.get_assistant_response(
        question=request.question,
        note_context=request.note_context,
        history=request.history
    )