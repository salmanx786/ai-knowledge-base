from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Knowledge Base"
    app_version: str = "0.1.0"
    debug: bool = True

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

    # Google Gemini settings for RAG chat. ``gemini_api_key`` is intentionally
    # optional (defaults to None): the app must boot without it so the rest of
    # the API stays available. The key is only required at the moment a chat is
    # generated -- ``llm.generate_answer`` raises a clear error if it is unset --
    # so a missing key surfaces as a server error on /api/v1/chat, not a failed
    # startup. The model is configurable so it can be swapped without a code change.
    gemini_api_key: str | None = None
    gemini_model: str = "gemini-2.5-flash"

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


settings = Settings()