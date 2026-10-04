from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Knowledge Base"
    app_version: str = "0.1.0"
    # Off by default so production never echoes SQL. ``engine`` uses this for
    # ``echo=``; set ``DEBUG=true`` in a dev ``.env`` to see statements.
    debug: bool = False

    database_url: str

    # JWT signing. `jwt_secret` is required and has no default on purpose:
    # a missing secret should fail fast at startup rather than fall back to a
    # guessable value. HS256 (symmetric HMAC) is the right choice while a
    # single service both issues and verifies tokens; switch to an RS/ES
    # asymmetric algorithm only when verification moves to a separate service.
    jwt_secret: str
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # Local filesystem root for uploaded documents. Files are saved under
    # ``<upload_dir>/<owner_id>/``; the directory is created on first upload.
    upload_dir: str = "uploads"

    # Google Gemini settings for RAG chat and embeddings
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    # S3 Storage settings for uploaded documents
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_region: str = "us-east-1"
    aws_endpoint_url: str | None = None
    aws_bucket_name: str = "ai-knowledge-base-uploads"

    # Maximum allowed size for uploaded files in megabytes.
    max_upload_size_mb: int = 10


    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()