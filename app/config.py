from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Support Ticket Triage Assistant"
    database_url: str = "sqlite:///./support_triage.db"
    openai_api_key: str | None = None
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    use_mock_ai: bool = True
    chroma_persist_directory: str = "./data/chroma"
    faq_directory: str = "./data/faqs"
    classification_confidence_threshold: float = 0.75
    validation_confidence_threshold: float = 0.80
    retrieval_score_threshold: float = 0.35
    api_base_url: str = "http://localhost:8000"

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


@lru_cache
def get_settings() -> Settings:
    return Settings()

