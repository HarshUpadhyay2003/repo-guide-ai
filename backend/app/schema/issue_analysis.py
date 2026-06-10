from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IssueInput(BaseModel):
    """Input payload for beginner-friendly issue analysis."""

    model_config = ConfigDict(extra="forbid")

    issue: Dict[str, Any] = Field(..., description="Issue title, body, and labels")
    repo_summary: Dict[str, Any] = Field(..., description="Repository summary context")
    repository_map: Dict[str, Any] = Field(..., description="Repository map context")
    comments: List[Dict[str, Any]] = Field(default_factory=list, description="Issue comments")

    @field_validator("issue")
    @classmethod
    def validate_issue(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("issue must be an object")

        title = value.get("title", "")
        body = value.get("body", "")
        labels = value.get("labels", [])

        if not isinstance(title, str) or not title.strip():
            raise ValueError("issue.title must be a non-empty string")
        if not isinstance(body, str):
            raise ValueError("issue.body must be a string")
        if not isinstance(labels, list) or not all(isinstance(item, str) for item in labels):
            raise ValueError("issue.labels must be an array of strings")

        return value

    @field_validator("repo_summary")
    @classmethod
    def validate_repo_summary(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("repo_summary must be an object")
        return value
        
    @field_validator("repository_map")
    @classmethod
    def validate_repository_map(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("repository_map must be an object")
        return value

    @field_validator("comments")
    @classmethod
    def validate_comments(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            raise ValueError("comments must be an array")
        return value


class IssueAnalysisOutput(BaseModel):
    """Structured beginner-friendly explanation of a GitHub issue."""

    model_config = ConfigDict(extra="forbid")

    difficulty: str = Field(..., pattern=r"^(Beginner|Intermediate|Advanced)$")
    skills_required: List[str] = Field(default_factory=list)
    affected_area: str = Field(..., min_length=1)
    beginner_explanation: str = Field(..., min_length=1)
    confidence_score: int = Field(..., ge=0, le=100)

    @field_validator("skills_required")
    @classmethod
    def validate_lists(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("List fields must contain non-empty strings")
        return [item.strip() for item in value]

    @field_validator("affected_area", "beginner_explanation")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Text fields must be non-empty strings")
        return value.strip()
