# app/features/quiz/endpoints.py
import logging
from fastapi import APIRouter, HTTPException, status, Body
from app.features.quiz.schemas import QuizRequest, QuizResponse
from app.features.quiz import quiz_service
from app.features.quiz.config import quiz_settings

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post(
    "/",
    response_model=QuizResponse,
    summary="Generate a Quiz",
    description="Generates a multi-question quiz based on general knowledge or user-provided context. The entire quiz, including grading logic and hints, is contained in the response.",
    tags=["V1 - Quiz"]
)
async def generate_quiz_endpoint(
    request: QuizRequest = Body(
        ...,
        examples={
            "context_based": {
                "summary": "Quiz from Text",
                "value": {
                    "mode": "user_context",
                    "questions": 3,
                    "difficulty": "For a high-school student",
                    "context": "The Treaty of Versailles was the most important of the peace treaties that brought World War I to an end. The Treaty ended the state of war between Germany and the Allied Powers. It was signed on 28 June 1919 in the Palace of Versailles, exactly five years after the assassination of Archduke Franz Ferdinand."
                }
            },
            "general_knowledge": {
                "summary": "General Knowledge Quiz",
                "value": {
                    "mode": "general",
                    "questions": 5,
                    "difficulty": "Capital cities of Europe"
                }
            },
        }
    )
):
    """
    Generates a self-contained quiz based on specified parameters.

    - **mode**: Determines the knowledge source.
      - `general`: Uses the LLM's general knowledge.
      - `user_context`: Requires the `context` field and bases the quiz on that text.
      - `hybrid`: Uses the provided `context` but allows the LLM to pull in related general knowledge.
    - **questions**: Number of questions to generate (capped at 20).
    - **difficulty**: A string to guide the LLM's tone and complexity.
    - **context**: A string of text required for `user_context` and `hybrid` modes.
    """
    # Use the safety cap from config
    if request.questions > quiz_settings.QUIZ_MAX_QUESTIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Number of questions cannot exceed the maximum of {quiz_settings.QUIZ_MAX_QUESTIONS}."
        )

    try:
        response = await quiz_service.generate_quiz(request)

        if response.error_message:
            # Determine the appropriate status code
            if "LLM API Error" in response.error_message:
                status_code = status.HTTP_502_BAD_GATEWAY
            elif "'context' field is required" in response.error_message:
                 status_code = status.HTTP_422_UNPROCESSABLE_ENTITY
            else:
                status_code = status.HTTP_500_INTERNAL_SERVER_ERROR

            raise HTTPException(
                status_code=status_code,
                detail=response.error_message
            )

        return response

    except HTTPException:
        raise # Re-raise exceptions we've already processed
    except Exception as e:
        logger.exception(f"Unexpected error in /quiz endpoint for mode '{request.mode}': {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"An unexpected error occurred while processing the quiz request: {str(e)}"
        )