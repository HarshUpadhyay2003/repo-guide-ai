import time
from typing import Any, Dict

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field, field_validator

from app.core.cache.dependencies import get_cache_manager
from app.core.cache.manager import CacheManager
from app.services.repo_service import RepoService
from app.utils.url_validation import validate_github_url

router = APIRouter(prefix="/repo", tags=["repo"])


class RepoAnalyzeRequest(BaseModel):
    url: str = Field(..., min_length=1, description="GitHub repository URL")

    @field_validator("url")
    @classmethod
    def check_github_url(cls, v: str) -> str:
        validate_github_url(v)
        return v


class RepoAnalyzeResponse(BaseModel):
    metadata: Dict[str, Any]
    summary: Dict[str, Any]
    repository_map: Dict[str, Any]
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
    request_start = time.perf_counter()
    try:
        result = service.analyze_repository(payload.url)

        validation_start = time.perf_counter()
        response_obj = RepoAnalyzeResponse(**result)
        validation_dur = time.perf_counter() - validation_start

        serialization_start = time.perf_counter()
        # Serialize to JSON to measure JSON serialization overhead
        response_obj.model_dump_json()
        serialization_dur = time.perf_counter() - serialization_start

        # Print structured performance report to terminal
        metrics = getattr(service, "metrics", {})
        if metrics:
            metrics["pydantic_validation"] = validation_dur
            metrics["json_serialization"] = serialization_dur

        return response_obj
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=str(exc)) from exc


@router.get("/analysis", response_model=RepoAnalyzeResponse, status_code=status.HTTP_200_OK)
def get_cached_repository_analysis(
    owner: str,
    repo: str,
    cache_mgr: CacheManager = Depends(get_cache_manager),
) -> RepoAnalyzeResponse:
    """Retrieve an existing repository analysis snapshot from cache if available."""
    snapshot = cache_mgr.get_analysis(owner, repo)
    if not snapshot:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis not found. Please analyze the repository first.",
        )
    return RepoAnalyzeResponse(**snapshot)
