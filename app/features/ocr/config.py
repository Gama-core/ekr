# app/features/ocr/config.py
from pydantic import BaseModel, Field

class OcrFeatureSettings(BaseModel):
    OCR_TIMEOUT_SECONDS: int = Field(
        default=90,
        description="Timeout in seconds for a single OCR API call."
    )

ocr_settings = OcrFeatureSettings()