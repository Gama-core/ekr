# app/schemas/agent.py
from pydantic import BaseModel, Field
from typing import List, Optional

class AgentQueryRequest(BaseModel):
    user_query: str = Field(..., description="The user's original question or prompt.")

class AgentStep(BaseModel):
    step_name: str
    details: str

class AgentResponse(BaseModel):
    final_answer: str
    intermediate_steps: List[AgentStep] = []
    source_url_crawled: Optional[str] = None