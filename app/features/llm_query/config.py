# app/features/llm_query/config.py
from pydantic import BaseModel, Field

# API keys and base URLs for LLMs are available via the global core.settings.
# This config can hold feature-specific defaults or operational parameters.

class LLMQueryFeatureSettings(BaseModel):
    DEFAULT_MAX_TOKENS: int = Field(
        default=1500,
        description="Default maximum number of tokens for LLM responses in this feature."
    )
    DEFAULT_TEMPERATURE: float = Field(
        default=0.7,
        ge=0.0,
        le=2.0,
        description="Default temperature for LLM generation (0.0 to 2.0)."
    )
    # You could add other LLM parameters here if needed, e.g., top_p, presence_penalty

# Global instance of LLM Query operational settings.
llm_query_settings = LLMQueryFeatureSettings()