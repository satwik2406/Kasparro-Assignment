"""
Configuration settings for AI Resume Screening & Ranking System.
Loads environment variables and sets baseline weights and thresholds.
"""

import os
from pathlib import Path
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # GitHub Enrichment Settings
    github_token: str = Field(default="", alias="GITHUB_TOKEN")
    github_cache_ttl_seconds: int = Field(default=3600, alias="GITHUB_CACHE_TTL_SECONDS")

    # LLM Settings
    llm_provider: str = Field(default="auto", alias="LLM_PROVIDER")  # "gemini", "openai", "auto", "rule-based"
    gemini_api_key: str = Field(default="", alias="GEMINI_API_KEY")
    openai_api_key: str = Field(default="", alias="OPENAI_API_KEY")
    openai_base_url: str = Field(default="https://api.openai.com/v1", alias="OPENAI_BASE_URL")
    llm_model: str = Field(default="gemini-1.5-flash", alias="LLM_MODEL")

    # Concurrency and Performance
    max_concurrency: int = Field(default=5, alias="MAX_CONCURRENT_REQUESTS")
    request_timeout_seconds: int = Field(default=15, alias="REQUEST_TIMEOUT_SECONDS")

    # Scoring Weights (100 total)
    weight_ai_project_depth: int = Field(default=40, alias="WEIGHT_AI_PROJECT_DEPTH")
    weight_python_backend: int = Field(default=30, alias="WEIGHT_PYTHON_BACKEND")
    weight_cloud_fullstack: int = Field(default=15, alias="WEIGHT_CLOUD_FULLSTACK")
    weight_github_activity: int = Field(default=10, alias="WEIGHT_GITHUB_ACTIVITY")
    weight_engineering_depth: int = Field(default=5, alias="WEIGHT_ENGINEERING_DEPTH")

    # Penalty configurations
    thin_wrapper_penalty_min: int = 5
    thin_wrapper_penalty_max: int = 15
    tutorial_project_penalty: int = 8


# Singleton instance
settings = Settings()
