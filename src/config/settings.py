"""
Configuration management for SmartSelf AI
Handles environment variables and application settings.
"""

import os
from functools import lru_cache
from pathlib import Path
from typing import List, Optional

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings with environment variable support"""

    # Application
    app_name: str = "SmartSelf AI"
    app_version: str = "1.0.0"
    debug: bool = Field(default=False, env="DEBUG")
    env: str = Field(default="local", env="ENV")  # local | staging | production
    json_logs: bool = Field(default=False, env="JSON_LOGS")

    # Security
    secret_key: str = Field(..., env="SECRET_KEY")  # REQUIRED — no default
    cors_origins: str = Field(default="*", env="CORS_ORIGINS")

    # API Keys
    openai_api_key: Optional[str] = Field(default=None, env="OPENAI_API_KEY")
    deepseek_api_key: Optional[str] = Field(default=None, env="DEEPSEEK_API_KEY")
    gemini_api_key: Optional[str] = Field(default=None, env="GEMINI_API_KEY")
    gemini_model: str = Field(default="gemini-flash-latest", env="GEMINI_MODEL")
    # gemini (free-tier friendly via Google AI Studio) | deepseek — must match get_llm_client() in web_server
    llm_provider: str = Field(default="deepseek", env="LLM_PROVIDER")

    # Server
    host: str = Field(default="0.0.0.0", env="HOST")
    port: int = Field(default=8000, env="PORT")

    # Database
    database_url: str = Field(default="sqlite:///./smartself.db", env="DATABASE_URL")

    # Vector Database
    chromadb_host: str = Field(default="localhost", env="CHROMADB_HOST")
    chromadb_port: int = Field(default=8001, env="CHROMADB_PORT")
    qdrant_host: str = Field(default="localhost", env="QDRANT_HOST")
    qdrant_port: int = Field(default=6333, env="QDRANT_PORT")
    qdrant_url: Optional[str] = Field(default=None, env="QDRANT_URL")

    # LLM runtime
    use_local_llm: bool = Field(default=False, env="USE_LOCAL_LLM")

    # Redis & Celery
    redis_url: str = Field(default="redis://localhost:6379/0", env="REDIS_URL")
    celery_broker_url: str = Field(default="redis://localhost:6379/1", env="CELERY_BROKER_URL")
    celery_result_backend: str = Field(
        default="redis://localhost:6379/1", env="CELERY_RESULT_BACKEND"
    )

    # Learning Configuration
    max_concurrent_crawls: int = Field(default=10, env="MAX_CONCURRENT_CRAWLS")
    crawl_rate_limit: int = Field(default=1, env="CRAWL_RATE_LIMIT")
    daily_crawl_limit: int = Field(default=1000, env="DAILY_CRAWL_LIMIT")
    min_quality_score: float = Field(default=0.3, env="MIN_QUALITY_SCORE")

    # Paths
    project_root: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent)
    data_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "data")
    logs_dir: Path = Field(default_factory=lambda: Path(__file__).parent.parent.parent / "logs")

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8",
        "case_sensitive": False,
        "extra": "allow",
    }

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        # Ensure directories exist
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.logs_dir.mkdir(parents=True, exist_ok=True)
        # Validate production settings on startup
        self.validate_production()

    def validate_production(self) -> None:
        """Crash loudly if critical settings are missing in production."""
        if self.is_production:
            if self.database_url.startswith("sqlite"):
                raise ValueError(
                    "SQLite is not allowed in production. Set DATABASE_URL to a PostgreSQL URL."
                )
            if self.secret_key == "dev-secret-key-change-in-production":
                raise ValueError("SECRET_KEY must be changed for production.")

    @property
    def is_production(self) -> bool:
        return self.env.lower() == "production"

    @property
    def environment(self) -> str:
        return self.env

    @property
    def project_name(self) -> str:
        return self.app_name

    @property
    def version(self) -> str:
        return self.app_version

    @property
    def jwt_secret_key(self) -> SecretStr:
        return SecretStr(self.secret_key)

    @property
    def cors_origin_list(self) -> List[str]:
        if self.cors_origins.strip() == "*":
            return ["*"]
        return [origin.strip() for origin in self.cors_origins.split(",") if origin.strip()]

    @property
    def database_url_sync(self) -> str:
        url = self.database_url
        if url.startswith("postgresql+asyncpg"):
            return url.replace("postgresql+asyncpg", "postgresql", 1)
        return url

    @property
    def qdrant_endpoint(self) -> str:
        if self.qdrant_url:
            return self.qdrant_url.rstrip("/")
        return f"http://{self.qdrant_host}:{self.qdrant_port}"


@lru_cache()
def get_settings() -> Settings:
    """Get cached settings instance"""
    return Settings()
