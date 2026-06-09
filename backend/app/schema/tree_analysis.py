from typing import Any, Dict, List

from pydantic import BaseModel, ConfigDict, Field, field_validator


class TreeInput(BaseModel):
    """Input payload for repository folder analysis."""

    model_config = ConfigDict(extra="forbid")

    tree: Dict[str, Any] = Field(..., description="Repository tree mapping folder names to child folders")
    repo_summary: Dict[str, Any] = Field(..., description="Repository summary context")

    @field_validator("tree")
    @classmethod
    def validate_tree(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("tree must be an object")
        return value

    @field_validator("repo_summary")
    @classmethod
    def validate_repo_summary(cls, value: Dict[str, Any]) -> Dict[str, Any]:
        if not isinstance(value, dict):
            raise ValueError("repo_summary must be an object")
        return value


class FolderInsight(BaseModel):
    """Basic explanation for one top-level folder."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(..., min_length=1)
    purpose: str = Field(..., min_length=1)
    difficulty: str = Field(..., pattern=r"^(Easy|Medium|Hard)$")
    should_beginner_touch: bool = Field(...)
    learning_priority: int = Field(..., ge=1, le=5)


class TreeAnalysisOutput(BaseModel):
    """Structured beginner-focused explanation of repository folders."""

    model_config = ConfigDict(extra="forbid")

    folders: List[FolderInsight] = Field(default_factory=list)
    best_folder_for_beginners: str = Field(..., min_length=1)
    recommended_exploration_order: List[str] = Field(default_factory=list)

    @field_validator("folders")
    @classmethod
    def validate_folders(cls, value: List[FolderInsight]) -> List[FolderInsight]:
        if not isinstance(value, list):
            raise ValueError("folders must be an array")
        return value

    @field_validator("recommended_exploration_order")
    @classmethod
    def validate_order(cls, value: List[str]) -> List[str]:
        if not isinstance(value, list) or not all(isinstance(item, str) and item.strip() for item in value):
            raise ValueError("recommended_exploration_order must contain non-empty strings")
        return [item.strip() for item in value]
