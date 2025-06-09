# app/features/mindmap_generator/schemas.py
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any

from app.features.llm_query.schemas import LLMUsageInfo

class MindmapRequest(BaseModel):
    text_content: str = Field(
        ...,
        min_length=20,
        description="The text content or information to be converted into a mind map."
    )
    root_node_name: Optional[str] = Field(
        default="Root",
        description="The desired name for the root node of the mind map."
    )
    extra_llm_params: Optional[Dict[str, Any]] = Field(
        None,
        description="Optional pass-through settings for the LLM, like 'temperature' or 'top_p', overriding feature defaults."
    )

    model_config = {
        "json_schema_extra": {
            "examples": [
                {
                    "text_content": "The solar system consists of the Sun and everything that orbits it, including eight planets. The inner, rocky planets are Mercury, Venus, Earth, and Mars. The outer planets are gas giants Jupiter and Saturn and ice giants Uranus and Neptune. Beyond Neptune is the Kuiper Belt.",
                    "root_node_name": "Solar System"
                }
            ]
        }
    }


class MindmapResponse(BaseModel):
    mermaid_code: Optional[str] = Field(
        None,
        description="The generated Mermaid.js mind map code."
    )
    model_used: Optional[str] = Field(
        None,
        description="The actual LLM model that processed the request."
    )
    usage_info: Optional[LLMUsageInfo] = Field(
        None,
        description="Information about token usage."
    )
    error_message: Optional[str] = Field(
        None,
        description="Error message if the mind map generation failed."
    )