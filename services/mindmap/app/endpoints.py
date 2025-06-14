import logging
from fastapi import APIRouter, HTTPException, status

from .schemas import MindmapRequest, MindmapResponse
from . import service

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate", response_model=MindmapResponse, summary="Generate Mermaid Mind Map Code")
async def generate_mindmap_endpoint(request: MindmapRequest):
    """Takes a block of text and converts it into Mermaid.js mind map syntax."""
    try:
        response = await service.generate_mindmap(request)
        if response.error_message:
            status_code = status.HTTP_502_BAD_GATEWAY if "LLM Service" in response.error_message else status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(status_code=status_code, detail=response.error_message)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /generate endpoint: {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")