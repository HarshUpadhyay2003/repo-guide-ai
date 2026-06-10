import logging
import time
from typing import Any, Dict, Optional

from fastapi import APIRouter
from pydantic import BaseModel, ConfigDict, Field

from app.prompts.repo_summary import REPO_SUMMARY_PROMPT
from app.services.exploration_hints_service import ExplorationHintsService
from app.services.github_service import GitHubService
from app.services.issue_service import IssueService
from app.services.llm_service import LLMService
from app.services.repo_service import RepoService
from app.services.repository_map_service import RepositoryMapService
from app.services.roadmap_service import RoadmapService
from app.utils.github_parser import parse_github_url

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/test", tags=["Testing"])

# -----------------------------------------------------------------------------
# Request / Response Schemas
# -----------------------------------------------------------------------------

class TestRepoRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {"repo_url": "https://github.com/langchain-ai/langchain"}
        }
    )


class TestIssueRequest(BaseModel):
    repo_url: str = Field(..., description="GitHub repository URL")
    issue_number: int = Field(..., description="GitHub issue number")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "repo_url": "https://github.com/langchain-ai/langchain",
                "issue_number": 12345
            }
        }
    )


class TestResponse(BaseModel):
    success: bool = Field(..., description="Whether the test executed successfully")
    execution_time_seconds: float = Field(..., description="Time taken to execute in seconds")
    data: Optional[Dict[str, Any]] = Field(None, description="The test output payload")
    error: Optional[str] = Field(None, description="Error message if the test failed")


# -----------------------------------------------------------------------------
# Helper Functions for Context Gathering
# -----------------------------------------------------------------------------

def _fetch_issue_data(gh: GitHubService, owner: str, repo: str, issue_number: int) -> Dict[str, Any]:
    """Helper to fetch a single raw issue formatted like get_good_first_issues."""
    repo_obj = gh._safe_repo(owner, repo)
    if not repo_obj:
        raise ValueError(f"Repository {owner}/{repo} not accessible.")
    
    issue = repo_obj.get_issue(issue_number)
    labels = [label.name.lower() for label in getattr(issue, "labels", [])]
    
    return {
        "number": issue.number,
        "title": issue.title,
        "body": (issue.body or "")[:500],
        "url": issue.html_url,
        "labels": sorted(labels)
    }


def _generate_test_summary(gh: GitHubService, llm: LLMService, owner: str, repo: str) -> Dict[str, Any]:
    """Helper to dynamically generate a repo summary for downstream testing."""
    metadata = gh.get_repo_metadata(owner, repo)
    readme = (gh.get_readme(owner, repo) or "")[:10000]
    contributing = (gh.get_contributing(owner, repo) or "")[:5000]
    prompt = REPO_SUMMARY_PROMPT.format(readme=readme, contributing=contributing, metadata=metadata)
    return llm.generate_json(prompt)


# -----------------------------------------------------------------------------
# Endpoints
# -----------------------------------------------------------------------------

@router.post(
    "/repository-map",
    response_model=TestResponse,
    summary="Test Repository Map Generation",
    description="Runs RepositoryMapService independently and returns the categorized repository structure."
)
def test_repository_map(request: TestRepoRequest):
    start_time = time.perf_counter()
    try:
        parsed = parse_github_url(request.repo_url)
        service = RepositoryMapService()
        result = service.generate_map(parsed["owner"], parsed["repo"])
        
        return TestResponse(
            success=True,
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            data={"repository_map": result}
        )
    except Exception as exc:
        logger.exception("Test /repository-map failed")
        return TestResponse(success=False, execution_time_seconds=round(time.perf_counter() - start_time, 3), error=str(exc))


@router.post(
    "/good-first-issues",
    response_model=TestResponse,
    summary="Test Good First Issue Discovery",
    description="Tests GitHub issue discovery independently to verify search parameters and response structures."
)
def test_good_first_issues(request: TestRepoRequest):
    start_time = time.perf_counter()
    try:
        parsed = parse_github_url(request.repo_url)
        service = GitHubService()
        issues = service.get_good_first_issues(parsed["owner"], parsed["repo"])
        
        return TestResponse(
            success=True,
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            data={"issues": issues}
        )
    except Exception as exc:
        logger.exception("Test /good-first-issues failed")
        return TestResponse(success=False, execution_time_seconds=round(time.perf_counter() - start_time, 3), error=str(exc))


@router.post(
    "/issue-comments",
    response_model=TestResponse,
    summary="Test Issue Comment Retrieval",
    description="Tests issue comment retrieval independently and verifies truncation and ghost user handling."
)
def test_issue_comments(request: TestIssueRequest):
    start_time = time.perf_counter()
    try:
        parsed = parse_github_url(request.repo_url)
        service = GitHubService()
        comments = service.get_issue_comments(parsed["owner"], parsed["repo"], request.issue_number)
        
        return TestResponse(
            success=True,
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            data={"comments": comments}
        )
    except Exception as exc:
        logger.exception("Test /issue-comments failed")
        return TestResponse(success=False, execution_time_seconds=round(time.perf_counter() - start_time, 3), error=str(exc))


@router.post(
    "/repository-summary",
    response_model=TestResponse,
    summary="Test Repository Summary Generation",
    description="Tests repository summary generation independently using README and CONTRIBUTING files."
)
def test_repository_summary(request: TestRepoRequest):
    start_time = time.perf_counter()
    try:
        parsed = parse_github_url(request.repo_url)
        gh = GitHubService()
        llm = LLMService()
        summary = _generate_test_summary(gh, llm, parsed["owner"], parsed["repo"])
        
        return TestResponse(
            success=True,
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            data={"summary": summary}
        )
    except Exception as exc:
        logger.exception("Test /repository-summary failed")
        return TestResponse(success=False, execution_time_seconds=round(time.perf_counter() - start_time, 3), error=str(exc))


@router.post(
    "/issue-analysis",
    response_model=TestResponse,
    summary="Test Issue Service Analysis",
    description="Builds the required upstream context (summary, map, comments) and tests IssueService independently."
)
def test_issue_analysis(request: TestIssueRequest):
    start_time = time.perf_counter()
    try:
        parsed = parse_github_url(request.repo_url)
        owner, repo = parsed["owner"], parsed["repo"]
        
        gh = GitHubService()
        llm = LLMService()
        
        summary = _generate_test_summary(gh, llm, owner, repo)
        repo_map = RepositoryMapService(gh).generate_map(owner, repo)
        issue_data = _fetch_issue_data(gh, owner, repo, request.issue_number)
        comments = gh.get_issue_comments(owner, repo, request.issue_number)
        
        analysis = IssueService(llm).analyze_issue({
            "issue": issue_data,
            "repo_summary": summary,
            "repository_map": repo_map,
            "comments": comments
        })
        
        return TestResponse(
            success=True,
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            data={"analysis": analysis}
        )
    except Exception as exc:
        logger.exception("Test /issue-analysis failed")
        return TestResponse(success=False, execution_time_seconds=round(time.perf_counter() - start_time, 3), error=str(exc))


@router.post(
    "/exploration-hints",
    response_model=TestResponse,
    summary="Test Exploration Hints Generation",
    description="Builds upstream context, resolves the issue analysis, and runs ExplorationHintsService independently."
)
def test_exploration_hints(request: TestIssueRequest):
    start_time = time.perf_counter()
    try:
        parsed = parse_github_url(request.repo_url)
        owner, repo = parsed["owner"], parsed["repo"]
        
        gh = GitHubService()
        llm = LLMService()
        
        summary = _generate_test_summary(gh, llm, owner, repo)
        repo_map = RepositoryMapService(gh).generate_map(owner, repo)
        issue_data = _fetch_issue_data(gh, owner, repo, request.issue_number)
        comments = gh.get_issue_comments(owner, repo, request.issue_number)
        
        analysis = IssueService(llm).analyze_issue({
            "issue": issue_data,
            "repo_summary": summary,
            "repository_map": repo_map,
            "comments": comments
        })
        
        hints = ExplorationHintsService(llm).generate_hints({
            "repository_map": repo_map,
            "issue_analysis": analysis,
            "issue": issue_data,
            "comments": comments
        })
        
        return TestResponse(
            success=True,
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            data={"exploration_hints": hints}
        )
    except Exception as exc:
        logger.exception("Test /exploration-hints failed")
        return TestResponse(success=False, execution_time_seconds=round(time.perf_counter() - start_time, 3), error=str(exc))


@router.post(
    "/full-analysis",
    response_model=TestResponse,
    summary="Test Full MVP Pipeline",
    description="Runs the full RepoService pipeline end-to-end to validate overall application orchestration."
)
def test_full_analysis(request: TestRepoRequest):
    start_time = time.perf_counter()
    try:
        result = RepoService().analyze_repository(request.repo_url)
        return TestResponse(
            success=True,
            execution_time_seconds=round(time.perf_counter() - start_time, 3),
            data=result
        )
    except Exception as exc:
        logger.exception("Test /full-analysis failed")
        return TestResponse(success=False, execution_time_seconds=round(time.perf_counter() - start_time, 3), error=str(exc))