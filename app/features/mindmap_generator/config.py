# app/features/mindmap_generator/config.py
from pydantic import BaseModel, Field

class MindmapGeneratorSettings(BaseModel):
    """
    Configuration settings specific to the Mindmap Generation feature.
    """
    MINDMAP_MAX_TOKENS: int = Field(
        default=4096,
        description="Default maximum number of tokens for the LLM to generate for a mind map response."
    )
    MINDMAP_TEMPERATURE: float = Field(
        default=0.2,
        ge=0.0,
        le=2.0,
        description="Default temperature for mind map generation to ensure structured, accurate output."
    )

mindmap_generator_settings = MindmapGeneratorSettings()