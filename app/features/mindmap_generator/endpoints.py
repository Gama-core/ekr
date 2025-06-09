# app/features/mindmap_generator/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status

from app.features.mindmap_generator.schemas import MindmapRequest, MindmapResponse
from app.features.mindmap_generator import service as mindmap_service

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/",
    response_model=MindmapResponse,
    summary="Generate Mermaid Mind Map Code",
    description="Takes a block of text and converts it into Mermaid.js mind map syntax using an LLM guided by a strict syntax definition.",
    tags=["V1 - Mindmap Generator"]
)
async def generate_mindmap_endpoint(request: MindmapRequest):
    try:
        response = await mindmap_service.generate_mindmap(request)

        if response.error_message:
            status_code = status.HTTP_502_BAD_GATEWAY if "LLM API Error" in response.error_message else status.HTTP_500_INTERNAL_SERVER_ERROR
            raise HTTPException(
                status_code=status_code,
                detail=response.error_message
            )

        return response

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /mindmap endpoint: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the mind map request: {str(e)}"
        )