import datetime
import uuid
from pydantic import BaseModel, Field, conint, constr
from typing import List, Optional, Literal, Dict, Any

# --- Schemas for this service's API contract ---

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
    mode: Literal["user_context", "general", "hybrid"]
    questions: conint(ge=1, le=20)
    difficulty: Optional[str] = "medium"
    context: Optional[constr(min_length=50)] = None # type: ignore
    extra_llm_params: Optional[Dict[str, Any]] = None

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