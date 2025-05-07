# app/core/config.py
import os
from pydantic_settings import BaseSettings
# from typing import Optional # SYSTEM_USER_ID is now mandatory for this simplified approach

class Settings(BaseSettings):
    GOOGLE_API_KEY: str
    GOOGLE_CSE_ID: str

    DB_HOST: str = "localhost"
    DB_PORT: str = "5432"
    DB_USER: str = "postgres"
    DB_PASSWORD: str
    DB_NAME: str = "postgres"

    QWEN_API_KEY: str
    QWEN_BASE_URL: str
    QWEN_DEFAULT_MODEL: str = "qwen-plus"

    # SYSTEM_USER_ID is now always 1 for simplicity without auth
    SYSTEM_USER_ID: int = 1

    @property
    def SQLALCHEMY_DATABASE_URL(self) -> str:
        return f"postgresql://{self.DB_USER}:{self.DB_PASSWORD}@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"

    class Config:
        env_file = ".env"
        env_file_encoding = 'utf-8'

settings = Settings()