"""Application settings, loaded from environment / .env."""
from __future__ import annotations

from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "Toolkit Pro"
    environment: str = "development"
    secret_key: str = "dev-insecure-secret-change-me"
    cors_origins: str = "http://localhost:3000"

    # Database. Defaults to a local SQLite file so the scaffold runs with zero config.
    database_url: str = "sqlite:///./toolkitpro.db"

    # Temp file processing
    tmp_upload_dir: str = "/tmp/uploads"
    tmp_result_dir: str = "/tmp/results"
    temp_file_ttl_minutes: int = 10
    max_upload_mb: int = 50

    # Permanent storage (blog images, site assets). Served at /storage.
    storage_dir: str = "storage"

    # Public URL for sitemap / canonical
    site_url: str = "http://localhost:3000"

    @property
    def blog_images_dir(self) -> str:
        return f"{self.storage_dir}/blog-images"

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def max_upload_bytes(self) -> int:
        return self.max_upload_mb * 1024 * 1024


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
