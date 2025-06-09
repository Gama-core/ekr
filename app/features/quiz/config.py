# app/features/quiz/config.py
from pydantic import BaseModel, Field

class QuizFeatureSettings(BaseModel):
    """
    Configuration settings specific to the Quiz generation feature.
    """
    QUIZ_MAX_TOKENS: int = Field(
        default=3072,  # Increased default for potentially large JSON payloads
        description="Default maximum number of tokens for the LLM to generate for a full quiz response."
    )
    QUIZ_DEFAULT_TEMPERATURE: float = Field(
        default=0.4,  # Lower temperature for more deterministic and structured JSON output
        ge=0.0,
        le=2.0,
        description="Default temperature for quiz generation to balance creativity and accuracy."
    )
    QUIZ_MAX_QUESTIONS: int = Field(
        default=20,
        gt=0,
        description="Safety cap on the maximum number of questions that can be requested in a single API call."
    )

quiz_settings = QuizFeatureSettings()