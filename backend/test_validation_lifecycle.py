import logging
import pytest
import time
from unittest.mock import MagicMock, patch

from app.core.cache.dependencies import get_cache_manager
from app.services.invalidation_tracker import invalidation_tracker
from app.services.repo_service import RepoService


def test_successful_repository_cache_writes():
    """Verify that cache writes are successful if the repository generation is unchanged."""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    
    owner, repo = "pallets", "flask"
    repo_key = f"{owner}/{repo}"
    
    # Read starting generation
    start_gen = invalidation_tracker.get_generation(repo_key)
    
    # Establish active analysis thread generation context
    invalidation_tracker.set_thread_generation(start_gen, time.perf_counter())
    try:
        key = f"cache:v1:repo:{owner}/{repo}:summary"
        cache_mgr.set(key, {"summary": "flask summary"})
        
        # Verify the write was allowed
        assert cache_mgr.get(key) == {"summary": "flask summary"}
    finally:
        invalidation_tracker.clear_thread_generation()


def test_invalidation_during_analysis_skips_writes(caplog):
    """Verify that invalidation during analysis causes subsequent cache writes to be skipped."""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    
    owner, repo = "fastapi", "fastapi"
    repo_key = f"{owner}/{repo}"
    
    # Read starting generation
    start_gen = invalidation_tracker.get_generation(repo_key)
    
    # Establish active analysis thread generation context
    invalidation_tracker.set_thread_generation(start_gen, time.perf_counter())
    try:
        # Simulate invalidation occurring concurrently (increments generation in tracker)
        invalidation_tracker.increment_generation(repo_key)
        
        key = f"cache:v1:repo:{owner}/{repo}:summary"
        
        # Run under log capture level WARNING to verify telemetry
        with caplog.at_level(logging.WARNING):
            cache_mgr.set(key, {"summary": "stale data"})
            
        # Verify write was skipped
        assert cache_mgr.get(key) is None
        
        # Verify telemetry log attributes
        log_records = [r for r in caplog.records if "[CACHE_WRITE_SKIPPED]" in r.message]
        assert len(log_records) == 1
        message = log_records[0].message
        assert f"Repository: {repo_key}" in message
        assert f"Cache Key: {key}" in message
        assert f"Start Generation: {start_gen}" in message
        assert f"Current Generation: {start_gen + 1}" in message
        assert "Reason: Invalidation triggered during active analysis." in message
    finally:
        invalidation_tracker.clear_thread_generation()


def test_repository_isolation_during_invalidation():
    """Verify that invalidating Repository A does not affect Repository B analysis writes."""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    
    owner_a, repo_a = "django", "django"
    owner_b, repo_b = "rails", "rails"
    repo_key_a = f"{owner_a}/{repo_a}"
    repo_key_b = f"{owner_b}/{repo_b}"
    
    start_gen_a = invalidation_tracker.get_generation(repo_key_a)
    start_gen_b = invalidation_tracker.get_generation(repo_key_b)
    
    # Establish context for Repository B
    invalidation_tracker.set_thread_generation(start_gen_b, time.perf_counter())
    try:
        # Invalidate Repository A
        invalidation_tracker.increment_generation(repo_key_a)
        
        # Write to Repository B
        key_b = f"cache:v1:repo:{owner_b}/{repo_b}:summary"
        cache_mgr.set(key_b, {"summary": "rails summary"})
        
        # Verify Repository B write succeeded
        assert cache_mgr.get(key_b) == {"summary": "rails summary"}
    finally:
        invalidation_tracker.clear_thread_generation()


def test_non_repository_caches_unaffected():
    """Verify that non-repository-scoped cache keys are written normally, ignoring generation state."""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    
    # Arbitrary non-repository key
    key = "cache:v1:global:system_config"
    
    # Set active thread generation context
    invalidation_tracker.set_thread_generation(5, time.perf_counter())
    try:
        # Write global config
        cache_mgr.set(key, {"theme": "dark"})
        
        # Verify write succeeded (since it's not repo-scoped)
        assert cache_mgr.get(key) == {"theme": "dark"}
    finally:
        invalidation_tracker.clear_thread_generation()


def test_repo_service_integration():
    """Verify the full RepoService integration correctly handles valid analyses."""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    
    service = RepoService()
    
    def mock_internal(url, mode="FAST_MVP"):
        res = {"status": "complete"}
        cache_mgr.set("cache:v1:repo:mock-owner/mock-repo:analysis_snapshot", res)
        return res
        
    service._analyze_repository_internal = MagicMock(side_effect=mock_internal)
    
    # Run analysis
    url = "https://github.com/mock-owner/mock-repo"
    res = service.analyze_repository(url)
    
    assert res == {"status": "complete"}
    service._analyze_repository_internal.assert_called_once()
    
    # Verify that the complete snapshot key was successfully written to cache
    snapshot_key = "cache:v1:repo:mock-owner/mock-repo:analysis_snapshot"
    assert cache_mgr.get(snapshot_key) == {"status": "complete"}
