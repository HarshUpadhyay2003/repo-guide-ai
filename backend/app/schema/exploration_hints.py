from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ExplorationHintsInput(BaseModel):
    """Input payload for generating exploration hints."""

    model_config = ConfigDict(extra="forbid")

    repository_map: Dict[str, Any] = Field(..., description="Categorized repository directories")
    issue_analysis: Dict[str, Any] = Field(..., description="Beginner-friendly explanation of the issue")
    issue: Dict[str, Any] = Field(..., description="Raw issue data including title, body, and labels")
    comments: List[Dict[str, Any]] = Field(default_factory=list, description="Issue comments for maintainer hints")

    @field_validator("repository_map", "issue_analysis", "issue")
    @classmethod
    def validate_dicts(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Expected an object")
        return value

    @field_validator("comments")
    @classmethod
    def validate_comments(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            raise ValueError("comments must be an array")
        return value


class ExplorationHintsOutput(BaseModel):
    """Structured exploration hints for a beginner contributor."""

    model_config = ConfigDict(extra="forbid")

    affected_area: str = Field(..., min_length=1)
    likely_directories: List[str] = Field(default_factory=list)
    possible_files: List[str] = Field(default_factory=list)
    reasoning: str = Field(..., min_length=1)
    confidence: int = Field(..., ge=0, le=100)

    @field_validator("likely_directories", "possible_files")
    @classmethod
    def validate_lists(cls, value: List[str]) -> List[str]:
        return [item.strip() for item in value if isinstance(item, str) and item.strip()]

    @field_validator("affected_area", "reasoning")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Text fields must be non-empty strings")
        return value.strip()