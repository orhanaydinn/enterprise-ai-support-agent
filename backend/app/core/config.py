from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Define application configuration loaded from environment variables."""

    app_name: str = "Enterprise AI Support Agent"
    app_version: str = "0.3.0"
    debug: bool = False

    aws_region: str = "eu-west-2"
    bedrock_model_id: str = "global.amazon.nova-2-lite-v1:0"

    intent_confidence_threshold: float = Field(
        default=0.75,
        ge=0.0,
        le=1.0,
    )

    rag_top_k: int = Field(
        default=3,
        ge=1,
        le=20,
    )

    rag_minimum_score: float = Field(
        default=0.25,
        ge=0.0,
        le=1.0,
    )

    rag_chunk_size: int = Field(
        default=500,
        ge=100,
        le=5000,
    )

    rag_chunk_overlap: int = Field(
        default=80,
        ge=0,
        le=1000,
    )

    citation_excerpt_length: int = Field(
        default=220,
        ge=50,
        le=1000,
    )

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached application settings instance."""

    settings = Settings()

    if settings.rag_chunk_overlap >= settings.rag_chunk_size:
        raise ValueError(
            "RAG_CHUNK_OVERLAP must be smaller than RAG_CHUNK_SIZE."
        )

    return settings


settings = get_settings()