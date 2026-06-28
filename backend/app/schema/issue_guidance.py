from typing import Any, Dict, List
from pydantic import BaseModel, ConfigDict, Field
from app.schema.issue_analysis import IssueAnalysisOutput
from app.schema.exploration_hints import ExplorationHintsOutput

class IssueGuidanceInput(BaseModel):
    """Input payload for combined issue analysis and hints."""
    
    model_config = ConfigDict(extra="forbid")
    
    issue: Dict[str, Any] = Field(..., description="Issue title, body, and labels")
    repo_summary: Dict[str, Any] = Field(..., description="Repository summary context")
    repository_map: Dict[str, Any] = Field(..., description="Repository map context")
    comments: List[Dict[str, Any]] = Field(default_factory=list, description="Issue comments")
    all_files: List[str] = Field(default_factory=list, description="All files in repository tree")
    all_dirs: List[str] = Field(default_factory=list, description="All directories in repository tree")

class IssueGuidanceOutput(BaseModel):
    """Combined issue analysis and exploration hints."""
    
    model_config = ConfigDict(extra="forbid")
    
    analysis: IssueAnalysisOutput
    exploration_hints: ExplorationHintsOutput
