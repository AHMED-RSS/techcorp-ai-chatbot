from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


PROJECT_ROOT = Path(__file__).resolve().parent.parent


class Settings(BaseSettings):
    """Central configuration for the local TechCorp AI application."""

    model_config = SettingsConfigDict(
        env_file=PROJECT_ROOT / ".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = Field(
        default="TechCorp AI",
        alias="APP_NAME",
    )

    app_subtitle: str = Field(
        default="Local Agent Workspace",
        alias="APP_SUBTITLE",
    )

    app_env: Literal[
        "development",
        "testing",
        "production",
    ] = Field(
        default="development",
        alias="APP_ENV",
    )

    app_debug: bool = Field(
        default=True,
        alias="APP_DEBUG",
    )

    # Database
    database_host: str = Field(
        default="127.0.0.1",
        alias="DATABASE_HOST",
    )

    database_port: int = Field(
        default=5432,
        alias="DATABASE_PORT",
        ge=1,
        le=65535,
    )

    database_name: str = Field(
        default="techcorp_ai",
        alias="DATABASE_NAME",
    )

    database_user: str = Field(
        default="techcorp_app",
        alias="DATABASE_USER",
    )

    database_password: str = Field(
        default="",
        alias="DATABASE_PASSWORD",
    )

    database_echo: bool = Field(
        default=False,
        alias="DATABASE_ECHO",
    )

    database_pool_size: int = Field(
        default=5,
        alias="DATABASE_POOL_SIZE",
        ge=1,
        le=50,
    )

    database_max_overflow: int = Field(
        default=10,
        alias="DATABASE_MAX_OVERFLOW",
        ge=0,
        le=100,
    )

    database_pool_timeout: int = Field(
        default=30,
        alias="DATABASE_POOL_TIMEOUT",
        ge=1,
        le=300,
    )

    # Ollama
    ollama_host: str = Field(
        default="http://localhost:11434",
        alias="OLLAMA_HOST",
    )

    ollama_chat_model: str = Field(
        default="llama3.2",
        alias="OLLAMA_CHAT_MODEL",
    )

    ollama_embed_model: str = Field(
        default="nomic-embed-text",
        alias="OLLAMA_EMBED_MODEL",
    )

    ollama_vision_model: str = Field(
        default="llama3.2-vision",
        alias="OLLAMA_VISION_MODEL",
    )

    ollama_request_timeout: float = Field(
        default=120,
        alias="OLLAMA_REQUEST_TIMEOUT",
        ge=10,
        le=600,
    )

    ollama_max_retries: int = Field(
        default=2,
        alias="OLLAMA_MAX_RETRIES",
        ge=0,
        le=10,
    )

    # Agent
    agent_max_steps: int = Field(
        default=8,
        alias="AGENT_MAX_STEPS",
        ge=1,
        le=30,
    )

    agent_max_replans: int = Field(
        default=2,
        alias="AGENT_MAX_REPLANS",
        ge=0,
        le=5,
    )

    agent_reflection_enabled: bool = Field(
        default=True,
        alias="AGENT_REFLECTION_ENABLED",
    )

    agent_router_temperature: float = Field(
        default=0.1,
        alias="AGENT_ROUTER_TEMPERATURE",
        ge=0,
        le=2,
    )

    agent_default_temperature: float = Field(
        default=0.4,
        alias="AGENT_DEFAULT_TEMPERATURE",
        ge=0,
        le=2,
    )

    # Uploads
    max_upload_size_mb: int = Field(
        default=50,
        alias="MAX_UPLOAD_SIZE_MB",
        ge=1,
        le=500,
    )

    max_files_per_message: int = Field(
        default=10,
        alias="MAX_FILES_PER_MESSAGE",
        ge=1,
        le=50,
    )

    max_extracted_text_chars: int = Field(
        default=100_000,
        alias="MAX_EXTRACTED_TEXT_CHARS",
        ge=1_000,
    )

    allow_archive_uploads: bool = Field(
        default=True,
        alias="ALLOW_ARCHIVE_UPLOADS",
    )

    # Web search without API key
    web_search_enabled: bool = Field(
        default=True,
        alias="WEB_SEARCH_ENABLED",
    )

    web_search_provider: str = Field(
        default="duckduckgo",
        alias="WEB_SEARCH_PROVIDER",
    )

    web_search_max_results: int = Field(
        default=6,
        alias="WEB_SEARCH_MAX_RESULTS",
        ge=1,
        le=20,
    )

    # Storage
    chat_folder: Path = Field(
        default=Path("chats"),
        alias="CHAT_FOLDER",
    )

    document_folder: Path = Field(
        default=Path("memory/documents"),
        alias="DOCUMENT_FOLDER",
    )

    task_folder: Path = Field(
        default=Path("memory/tasks"),
        alias="TASK_FOLDER",
    )

    agent_run_folder: Path = Field(
        default=Path("memory/agent_runs"),
        alias="AGENT_RUN_FOLDER",
    )

    chroma_folder: Path = Field(
        default=Path("chroma_db"),
        alias="CHROMA_FOLDER",
    )

    upload_folder: Path = Field(
        default=Path("uploads"),
        alias="UPLOAD_FOLDER",
    )

    report_folder: Path = Field(
        default=Path("reports"),
        alias="REPORT_FOLDER",
    )

    skills_folder: Path = Field(
        default=Path("skills"),
        alias="SKILLS_FOLDER",
    )

    generated_image_folder: Path = Field(
        default=Path("generated_images"),
        alias="GENERATED_IMAGE_FOLDER",
    )

    log_folder: Path = Field(
        default=Path("logs"),
        alias="LOG_FOLDER",
    )

    @field_validator(
        "chat_folder",
        "document_folder",
        "task_folder",
        "agent_run_folder",
        "chroma_folder",
        "upload_folder",
        "report_folder",
        "skills_folder",
        "generated_image_folder",
        "log_folder",
        mode="after",
    )
    @classmethod
    def make_absolute(cls, value: Path) -> Path:
        if value.is_absolute():
            return value

        return PROJECT_ROOT / value

    def create_runtime_directories(self) -> None:
        folders = (
            self.chat_folder,
            self.document_folder,
            self.task_folder,
            self.agent_run_folder,
            self.chroma_folder,
            self.upload_folder,
            self.report_folder,
            self.skills_folder,
            self.generated_image_folder,
            self.log_folder,
        )

        for folder in folders:
            folder.mkdir(
                parents=True,
                exist_ok=True,
            )


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    settings = Settings()
    settings.create_runtime_directories()
    return settings