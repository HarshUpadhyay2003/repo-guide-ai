from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class RoadmapInput(BaseModel):
    """Input payload for contributor roadmap generation."""

    model_config = ConfigDict(extra="forbid")

    repo_summary: Dict[str, Any] = Field(..., description="Repository summary context")
    repository_map: Dict[str, Any] = Field(..., description="Repository folder structure")
    issues: List[Dict[str, Any]] = Field(default_factory=list, description="Candidate issues")
    all_files: List[str] = Field(default_factory=list, description="All files in repository tree")
    all_dirs: List[str] = Field(default_factory=list, description="All directories in repository tree")

    @field_validator("repo_summary", "repository_map")
    @classmethod
    def validate_dicts(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("Expected an object")
        return value

    @field_validator("issues")
    @classmethod
    def validate_issues(cls, value: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        if not isinstance(value, list):
            raise ValueError("issues must be an array")
        return value


class BestIssue(BaseModel):
    """Best issue recommendation for a beginner."""

    model_config = ConfigDict(extra="forbid")

    issue_number: int = Field(..., ge=1)
    title: str = Field(..., min_length=1)


class RoadmapOutput(BaseModel):
    """Structured contributor roadmap output."""

    model_config = ConfigDict(extra="forbid")

    best_issue_to_start: BestIssue
    why_this_issue: str = Field(..., min_length=1)
    recommended_learning_order: List[str] = Field(default_factory=list)
    files_to_read_first: List[str] = Field(default_factory=list)
    contribution_plan: List[str] = Field(default_factory=list)
    success_tips: List[str] = Field(default_factory=list)

    @field_validator("recommended_learning_order", "files_to_read_first", "contribution_plan", "success_tips")
    @classmethod
    def validate_lists(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("List fields must contain non-empty strings")
        return [item.strip() for item in value]
