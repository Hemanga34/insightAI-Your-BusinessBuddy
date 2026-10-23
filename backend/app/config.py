from functools import lru_cache
from pathlib import Path

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    database_url: str = "sqlite:///./data/insightai.db"
    jwt_secret: str
    token_minutes: int = 60
    upload_dir: Path = Path("./data/uploads")
    max_upload_bytes: int = 20 * 1024 * 1024
    task_mode: str = "celery"
    redis_url: str = "redis://localhost:6379/0"
    storage_backend: str = "local"
    s3_bucket: str = ""
    aws_region: str = "ap-south-1"
    cors_origins: list[str] = ["http://localhost:5173"]

    @model_validator(mode="after")
    def validate_configuration(self):
        if len(self.jwt_secret) < 32 or self.jwt_secret.startswith("replace-"):
            raise ValueError("JWT_SECRET must be a new random secret of at least 32 characters")
        if self.task_mode not in {"celery", "inline"}:
            raise ValueError("TASK_MODE must be celery or inline")
        if self.storage_backend not in {"local", "s3"}:
            raise ValueError("STORAGE_BACKEND must be local or s3")
        if self.storage_backend == "s3" and not self.s3_bucket:
            raise ValueError("S3_BUCKET is required for S3 storage")
        return self


@lru_cache
def get_settings() -> Settings:
    return Settings()
