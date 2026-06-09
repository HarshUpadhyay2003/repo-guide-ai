from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field

from app.services.repo_service import RepoService

router = APIRouter(prefix="/repo", tags=["repo"])


class RepoAnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1, description="GitHub repository URL")


class RepoAnalyzeResponse(BaseModel):
    metadata: Dict[str, Any]
    summary: Dict[str, Any]
    roadmap: Dict[str, Any]
    issues: list[Dict[str, Any]]


def get_repo_service() -> RepoService:
    return RepoService()


@router.post("/analyze", response_model=RepoAnalyzeResponse, status_code=status.HTTP_200_OK)
def analyze_repository(
    payload: RepoAnalyzeRequest,
    service: RepoService = Depends(get_repo_service),
) -> RepoAnalyzeResponse:
    """Analyze a GitHub repository and return summary, roadmap, and issues."""
    try:
        result = service.analyze_repository(payload.url)
        return RepoAnalyzeResponse(**result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc
