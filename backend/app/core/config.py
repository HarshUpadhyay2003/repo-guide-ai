import os
from functools import lru_cache
from pathlib import Path
from typing import Annotated, Final

from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict, StringConstraints, ValidationError

BASE_DIR: Final[Path] = Path(__file__).resolve().parents[2]
load_dotenv(BASE_DIR / ".env", override=False)


class Settings(BaseModel):
    """Application configuration loaded from environment variables and .env."""

    model_config = ConfigDict(extra="ignore", validate_default=True)

    GITHUB_TOKEN: Annotated[str, StringConstraints(min_length=1)]
    GROQ_API_KEY: Annotated[str, StringConstraints(min_length=1)]
    DATABASE_URL: Annotated[str, StringConstraints(min_length=1)]
    MODEL_NAME: Annotated[str, StringConstraints(min_length=1)]
    CACHE_BACKEND: str = "memory"
    REDIS_URL: str = ""
    SINGLEFLIGHT_TIMEOUT_SECONDS: int = 180
    ALLOWED_ORIGINS: list[str] = [
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "https://repo-guide-ai.vercel.app"
    ]
    MAX_PAYLOAD_SIZE_BYTES: int = 1048576  # 1 MB default limit
    RATE_LIMIT_ANALYZE_PER_MINUTE: int = 5
    RATE_LIMIT_PDF_PER_MINUTE: int = 10
    RATE_LIMIT_GENERAL_PER_MINUTE: int = 60
    RATE_LIMIT_HEALTH_PER_MINUTE: int = 120
    MAX_CONCURRENT_PDF_GENERATIONS: int = 3
    ENABLE_GZIP: bool = True
    GZIP_MINIMUM_SIZE: int = 1000
    ENABLE_HSTS: bool = False
    HSTS_MAX_AGE: int = 31536000

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from the current process environment after loading .env."""
        load_dotenv(BASE_DIR / ".env", override=False)
        default_origins = "http://localhost:3000,http://127.0.0.1:3000,https://repo-guide-ai.vercel.app"
        raw_origins = os.environ.get("ALLOWED_ORIGINS", default_origins)
        origins = [item.strip() for item in raw_origins.split(",") if item.strip()] if isinstance(raw_origins, str) else ["http://localhost:3000", "http://127.0.0.1:3000", "https://repo-guide-ai.vercel.app"]
        try:
            max_payload = int(os.environ.get("MAX_PAYLOAD_SIZE_BYTES", "1048576"))
        except ValueError:
            max_payload = 1048576

        def get_int_env(name: str, default: int) -> int:
            try:
                return int(os.environ.get(name, str(default)))
            except ValueError:
                return default

        def get_bool_env(name: str, default: bool) -> bool:
            val = os.environ.get(name)
            if val is None:
                return default
            return val.strip().lower() in ("true", "1", "yes", "on")

        return cls(
            GITHUB_TOKEN=os.environ.get("GITHUB_TOKEN", ""),
            GROQ_API_KEY=os.environ.get("GROQ_API_KEY", ""),
            DATABASE_URL=os.environ.get("DATABASE_URL", ""),
            MODEL_NAME=os.environ.get("MODEL_NAME", ""),
            CACHE_BACKEND=os.environ.get("CACHE_BACKEND", "memory"),
            REDIS_URL=os.environ.get("REDIS_URL", ""),
            SINGLEFLIGHT_TIMEOUT_SECONDS=os.environ.get("SINGLEFLIGHT_TIMEOUT_SECONDS", "180"),
            ALLOWED_ORIGINS=origins,
            MAX_PAYLOAD_SIZE_BYTES=max_payload,
            RATE_LIMIT_ANALYZE_PER_MINUTE=get_int_env("RATE_LIMIT_ANALYZE_PER_MINUTE", 5),
            RATE_LIMIT_PDF_PER_MINUTE=get_int_env("RATE_LIMIT_PDF_PER_MINUTE", 10),
            RATE_LIMIT_GENERAL_PER_MINUTE=get_int_env("RATE_LIMIT_GENERAL_PER_MINUTE", 60),
            RATE_LIMIT_HEALTH_PER_MINUTE=get_int_env("RATE_LIMIT_HEALTH_PER_MINUTE", 120),
            MAX_CONCURRENT_PDF_GENERATIONS=get_int_env("MAX_CONCURRENT_PDF_GENERATIONS", 3),
            ENABLE_GZIP=get_bool_env("ENABLE_GZIP", True),
            GZIP_MINIMUM_SIZE=get_int_env("GZIP_MINIMUM_SIZE", 1000),
            ENABLE_HSTS=get_bool_env("ENABLE_HSTS", False),
            HSTS_MAX_AGE=get_int_env("HSTS_MAX_AGE", 31536000),
        )


def _build_settings() -> Settings:
    """Create and validate settings with descriptive errors for missing values."""
    try:
        return Settings.from_env()
    except ValidationError as exc:
        missing_fields = [
            ".".join(str(item) for item in error["loc"])
            for error in exc.errors()
            if error["type"] in {"missing", "string_too_short"}
        ]

        if missing_fields:
            raise ValueError(
                "Missing required environment variables: " + ", ".join(missing_fields)
            ) from exc

        details = "; ".join(
            f"{'.'.join(str(item) for item in error['loc'])}: {error['msg']}"
            for error in exc.errors()
        )
        raise ValueError(f"Invalid environment configuration: {details}") from exc


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Return a cached settings instance for dependency injection."""
    return _build_settings()


settings = get_settings()
