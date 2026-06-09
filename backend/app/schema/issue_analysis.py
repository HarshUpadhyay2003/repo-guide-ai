from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class IssueInput(BaseModel):
    """Input payload for beginner-friendly issue analysis."""

    model_config = ConfigDict(extra="forbid")

    issue: Dict[str, Any] = Field(..., description="Issue title, body, and labels")
    repo_summary: Dict[str, Any] = Field(..., description="Repository summary context")

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


class IssueAnalysisOutput(BaseModel):
    """Structured beginner-friendly explanation of a GitHub issue."""

    model_config = ConfigDict(extra="forbid")

    difficulty: str = Field(..., pattern=r"^(Beginner|Intermediate|Advanced)$")
    estimated_hours: int = Field(..., ge=0, le=100)
    skills_required: List[str] = Field(default_factory=list)
    concepts_to_understand: List[str] = Field(default_factory=list)
    what_needs_to_be_done: str = Field(..., min_length=1)
    beginner_explanation: str = Field(..., min_length=1)
    files_likely_affected: List[str] = Field(default_factory=list)
    recommended_first_step: str = Field(..., min_length=1)
    confidence_score: int = Field(..., ge=0, le=100)

    @field_validator("skills_required", "concepts_to_understand", "files_likely_affected")
    @classmethod
    def validate_lists(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("List fields must contain non-empty strings")
        return [item.strip() for item in value]

    @field_validator("what_needs_to_be_done", "beginner_explanation", "recommended_first_step")
    @classmethod
    def validate_text(cls, value: str) -> str:
        if not isinstance(value, str) or not value.strip():
            raise ValueError("Text fields must be non-empty strings")
        return value.strip()
