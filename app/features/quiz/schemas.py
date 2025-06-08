# app/features/quiz/schemas.py
import datetime
import uuid
from pydantic import BaseModel, Field, conint, constr
from typing import List, Optional, Literal, Dict, Any, Union

# --- Nested Schemas for the Quiz Response ---

class QuizOption(BaseModel):
    option_id: str = Field(..., description="A unique identifier for the option, e.g., 'A', 'B', 'C'.")
    text: str = Field(..., description="The text content of the option.")
    is_correct: bool = Field(..., description="Boolean flag indicating if this is a correct answer.")
    hint: str = Field(..., description="Feedback to show to the user if they select this specific option.")

class QuizQuestion(BaseModel):
    id: int = Field(..., description="A sequential integer (1-n) for stable referencing within the quiz.")
    type: str = Field(..., description="The type of question, e.g., 'single', 'multi', 'boolean'.")
    points: float = Field(..., ge=0, description="Points awarded for a correct answer; allows fractional scores.")
    stem_md: str = Field(..., description="The main question text, formatted in Markdown.")
    code_block: Optional[str] = Field(None, description="An optional block of code related to the question.")
    options: List[QuizOption] = Field(..., description="A list of possible answer options for the question.")
    correct_option_ids: List[str] = Field(..., description="A list of the `option_id`s that are correct.")
    explanation: str = Field(..., description="A detailed explanation shown to the user after the question is answered.")


# --- API Request Schema ---

class QuizRequest(BaseModel):
    mode: Literal["user_context", "general", "hybrid"] = Field(
        ...,
        description="Specifies the knowledge source for the quiz."
    )
    questions: conint(ge=1, le=20) = Field(
        ...,
        description="The number of questions to generate."
    )
    difficulty: Optional[str] = Field(
        default="medium",
        description="A hint to the LLM about the desired difficulty (e.g., 'easy for a 5th grader', 'university-level computer science')."
    )
    context: Optional[constr(min_length=50)] = Field(  # type: ignore
        None,
        description="The raw text context to be used for generating the quiz. Required if mode is 'user_context' or 'hybrid'."
    )
    extra_llm_params: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional pass-through settings for the LLM, like 'temperature' or 'top_p'."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "mode": "user_context",
                    "questions": 3,
                    "difficulty": "easy",
                    "context": "The mitochondria is the powerhouse of the cell. It generates most of the cell's supply of adenosine triphosphate (ATP), used as a source of chemical energy."
                },
                {
                    "mode": "general",
                    "questions": 5,
                    "difficulty": "Challenging questions about World War II for a history buff."
                }
            ]
        }
    }

# --- API Response Schema ---

class QuizResponse(BaseModel):
    quiz_id: uuid.UUID = Field(default_factory=uuid.uuid4, description="A unique UUID for the generated quiz.")
    title: Optional[str] = Field(None, description="An optional, friendly title for the quiz if provided by the LLM.")
    generated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow, description="UTC timestamp of when the quiz was generated.")
    model_used: Optional[str] = Field(None, description="The identifier of the LLM that generated the quiz.")
    context_mode: Literal["user_context", "general", "hybrid"] = Field(..., description="Mirrors the requested 'mode' for traceability.")
    questions: List[QuizQuestion] = Field([], description="The list of generated quiz questions.")
    error_message: Optional[str] = Field(None, description="An error message if quiz generation failed.")