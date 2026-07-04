import time
import logging
from typing import Any, Dict
from fastapi import APIRouter, Depends, HTTPException, status, Response

from app.core.cache.dependencies import get_cache_manager
from app.core.cache.manager import CacheManager
from app.pdf.templates.repository_report import RepositoryReportTemplate
from app.pdf.templates.issue_report import IssueReportTemplate
from app.pdf.templates.contribution_report import ContributionReportTemplate

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/pdf", tags=["pdf"])


@router.get("/repository")
def get_repository_pdf(
    owner: str,
    repo: str,
    cache_mgr: CacheManager = Depends(get_cache_manager),
) -> Response:
    """Generate and return the Repository Guide PDF if analysis snapshot exists in cache."""
    snapshot = cache_mgr.get_analysis(owner, repo)
    if not snapshot:
        print("[PDF][Repository]")
        print("Snapshot Cache MISS\n")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis not found. Please analyze the repository first.",
        )

    print("[PDF][Repository]")
    print("Snapshot Cache HIT\n")
    print("Generating Repository PDF...\n")
    
    start_time = time.perf_counter()
    try:
        pdf_bytes = RepositoryReportTemplate.generate(repo_name=repo, analysis_data=snapshot)
    except Exception as exc:
        logger.exception("Failed to generate Repository PDF")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Repository PDF.",
        ) from exc
    
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    print(f"Generated in {elapsed_ms} ms\n")

    filename = f"{repo.lower()}_repository_guide.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/issue/{issue_number}")
def get_issue_pdf(
    issue_number: int,
    owner: str,
    repo: str,
    cache_mgr: CacheManager = Depends(get_cache_manager),
) -> Response:
    """Generate and return the Issue Guide PDF if analysis snapshot exists in cache."""
    snapshot = cache_mgr.get_analysis(owner, repo)
    if not snapshot:
        print("[PDF][Issue]")
        print("Snapshot Cache MISS\n")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis not found. Please analyze the repository first.",
        )

    # Locate the issue in snapshot
    matching_issue = None
    for issue_entry in snapshot.get("issues", []):
        raw = issue_entry.get("raw_issue", {})
        if str(raw.get("number")) == str(issue_number):
            matching_issue = issue_entry
            break

    if not matching_issue:
        print("[PDF][Issue]")
        print(f"Issue #{issue_number} not found in snapshot\n")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Issue #{issue_number} not found in the repository analysis snapshot.",
        )

    print("[PDF][Issue]")
    print("Snapshot Cache HIT\n")
    print("Generating Issue Guide PDF...\n")
    
    start_time = time.perf_counter()
    try:
        pdf_bytes = IssueReportTemplate.generate(issue_data=matching_issue, repo_name=repo)
    except Exception as exc:
        logger.exception("Failed to generate Issue PDF")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Issue PDF.",
        ) from exc
    
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    print(f"Generated in {elapsed_ms} ms\n")

    filename = f"{repo.lower()}_issue_{issue_number}_guide.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)


@router.get("/contribution")
def get_contribution_pdf(
    owner: str,
    repo: str,
    cache_mgr: CacheManager = Depends(get_cache_manager),
) -> Response:
    """Generate and return the Contribution Guide PDF if analysis snapshot exists in cache."""
    snapshot = cache_mgr.get_analysis(owner, repo)
    if not snapshot:
        print("[PDF][Contribution]")
        print("Snapshot Cache MISS\n")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository analysis not found. Please analyze the repository first.",
        )

    print("[PDF][Contribution]")
    print("Snapshot Cache HIT\n")
    print("Generating Contribution Guide PDF...\n")
    
    start_time = time.perf_counter()
    try:
        pdf_bytes = ContributionReportTemplate.generate(repo_name=repo, analysis_data=snapshot)
    except Exception as exc:
        logger.exception("Failed to generate Contribution PDF")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to generate Contribution PDF.",
        ) from exc
    
    elapsed_ms = int((time.perf_counter() - start_time) * 1000)
    print(f"Generated in {elapsed_ms} ms\n")

    filename = f"{repo.lower()}_contribution_guide.pdf"
    headers = {
        "Content-Disposition": f"attachment; filename={filename}",
        "Access-Control-Expose-Headers": "Content-Disposition",
    }
    return Response(content=pdf_bytes, media_type="application/pdf", headers=headers)
