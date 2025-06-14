from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

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


# --- Schemas for this service's API contract ---
class MindmapRequest(BaseModel):
    text_content: str = Field(..., min_length=20, description="The text to be converted into a mind map.")
    root_node_name: Optional[str] = Field("Root", description="The desired name for the root node.")
    extra_llm_params: Optional[Dict[str, Any]] = Field(None, description="Optional pass-through settings for the LLM.")

class MindmapResponse(BaseModel):
    mermaid_code: Optional[str] = Field(None, description="The generated Mermaid.js mind map code.")
    model_used: Optional[str] = Field(None, description="The actual LLM model that processed the request.")
    usage_info: Optional[LLMUsageInfo] = Field(None, description="Information about token usage.")
    error_message: Optional[str] = Field(None, description="Error message if generation failed.")