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

    @classmethod
    def from_env(cls) -> "Settings":
        """Build settings from the current process environment after loading .env."""
        load_dotenv(BASE_DIR / ".env", override=False)
        return cls(
            GITHUB_TOKEN=os.environ.get("GITHUB_TOKEN", ""),
            GROQ_API_KEY=os.environ.get("GROQ_API_KEY", ""),
            DATABASE_URL=os.environ.get("DATABASE_URL", ""),
            MODEL_NAME=os.environ.get("MODEL_NAME", ""),
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
