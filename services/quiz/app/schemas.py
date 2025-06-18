import datetime
import uuid
from pydantic import BaseModel, Field, conint, constr, ConfigDict
from typing import List, Optional, Literal

# --- Schemas for this service's API contract ---

# Defines the allowed types of questions
QuestionType = Literal["single-choice", "multi-select", "boolean"]

class QuizOption(BaseModel):
    option_id: str
    text: str
    is_correct: bool
    hint: str

class QuizQuestion(BaseModel):
    id: int
    type: str
    points: float
    stem_md: str
    code_block: Optional[str] = None
    options: List[QuizOption]
    correct_option_ids: List[str]
    explanation: str

class QuizRequest(BaseModel):
    mode: Literal["user_context", "general", "hybrid"] = Field(
        ...,
        description=(
            "**Required**. The mode for quiz generation.\n\n"
            "- `user_context`: Uses only the provided `context` text.\n"
            "- `general`: Uses the LLM's general knowledge (ignores `context`).\n"
            "- `hybrid`: Uses both the provided `context` and the LLM's knowledge."
        )
    )
    questions: conint(ge=1, le=20) = Field(
        ...,
        description="**Required**. The total number of questions to generate (must be between 1 and 20)."
    )
    difficulty: Optional[str] = Field(
        "medium",
        description="Optional. The desired difficulty level for the questions (e.g., 'easy', 'medium', 'hard')."
    )
    question_types: List[QuestionType] = Field(
        default=["single-choice"],
        description=(
            "Optional. A list of desired question types to generate.\n\n"
            "- `single-choice`: One correct answer from a list of options.\n"
            "- `multi-select`: One or more correct answers from a list of options.\n"
            "- `boolean`: A True or False question."
        )
    )
    include_code_block: Optional[bool] = Field(
        False,
        description="Optional. If `true`, the LLM will be encouraged to include relevant code blocks in the generated questions."
    )
    context: Optional[constr(min_length=50)] = Field( # type: ignore
        None,
        description="The source text to base the quiz on. **Required** when `mode` is 'user_context' or 'hybrid'."
    )

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "mode": "hybrid",
                    "questions": 3,
                    "difficulty": "medium",
                    "question_types": ["single-choice", "multi-select"],
                    "include_code_block": True,
                    "context": "In Python, a list is a mutable ordered sequence of elements. A tuple is an immutable ordered sequence. Lists are defined with square brackets `[]` and tuples with parentheses `()`. The `len()` function can be used to get the number of items in both."
                }
            ]
        }
    )

class QuizResponse(BaseModel):
    quiz_id: uuid.UUID = Field(default_factory=uuid.uuid4)
    title: Optional[str] = None
    generated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    model_used: Optional[str] = None
    context_mode: Literal["user_context", "general", "hybrid"]
    questions: List[QuizQuestion] = []
    error_message: Optional[str] = None

# --- Schemas for communicating with the LLM Query Service ---

class LLMUsageInfo(BaseModel):
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    total_tokens: Optional[int] = None

class LLMQueryResponse(BaseModel):
    response_text: Optional[str] = None
    model_used: Optional[str] = None
    usage_info: Optional[LLMUsageInfo] = None
    error_message: Optional[str] = None