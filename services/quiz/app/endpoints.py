import logging
from fastapi import APIRouter, HTTPException, status, Body

from .schemas import QuizRequest, QuizResponse
from . import service
from .config import settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/generate", response_model=QuizResponse, summary="Generate a Quiz")
async def generate_quiz_endpoint(request: QuizRequest):
    """Generates a multi-question quiz based on the provided specifications."""
    if request.questions > settings.QUIZ_MAX_QUESTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Number of questions cannot exceed the maximum of {settings.QUIZ_MAX_QUESTIONS}."
        )
    try:
        response = await service.generate_quiz(request)
        if response.error_message:
            status_code = status.HTTP_502_BAD_GATEWAY if "LLM Service" in response.error_message else status.HTTP_422_UNPROCESSABLE_ENTITY
            raise HTTPException(status_code=status_code, detail=response.error_message)
        return response
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Unexpected error in /generate endpoint for mode '{request.mode}': {e}")
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"An unexpected error occurred: {e}")