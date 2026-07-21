import pytest
from app.core.cache.dependencies import get_cache_manager
from app.core.cache.keys import get_repo_summary_key, get_repo_map_key, get_analysis_snapshot_key
from app.services.invalidation_tracker import invalidation_tracker


def test_prefix_invalidation():
    """Verify that CacheManager.invalidate_pattern clears keys matching the prefix."""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    
    # Write some keys
    key1 = "cache:v1:repo:pallets/flask:summary"
    key2 = "cache:v1:repo:pallets/flask:map"
    key3 = "cache:v1:repo:django/django:summary"
    
    cache_mgr.set(key1, {"summary": "flask summary"})
    cache_mgr.set(key2, {"map": "flask map"})
    cache_mgr.set(key3, {"summary": "django summary"})
    
    # Assert they exist
    assert cache_mgr.get(key1) == {"summary": "flask summary"}
    assert cache_mgr.get(key2) == {"map": "flask map"}
    assert cache_mgr.get(key3) == {"summary": "django summary"}
    
    # Invalidate pallets/flask keys using prefix pattern
    prefix = "cache:v1:repo:pallets/flask:"
    cache_mgr.invalidate_pattern(prefix)
    
    # Verify pallets/flask keys are gone, but django/django remains
    assert cache_mgr.get(key1) is None
    assert cache_mgr.get(key2) is None
    assert cache_mgr.get(key3) == {"summary": "django summary"}


def test_generation_increment_on_invalidation():
    """Verify that calling invalidate_repository increments the repository's generation version."""
    cache_mgr = get_cache_manager()
    repo_owner = "fastapi"
    repo_name = "fastapi"
    repo_key = f"{repo_owner}/{repo_name}"
    
    # Get current generation
    start_gen = invalidation_tracker.get_generation(repo_key)
    
    # Trigger invalidation
    cache_mgr.invalidate_repository(repo_owner, repo_name)
    
    # Verify generation is incremented
    new_gen = invalidation_tracker.get_generation(repo_key)
    assert new_gen == start_gen + 1


def test_repository_invalidation_isolation():
    """Verify that invalidating one repository leaves other repositories untouched (isolation)."""
    cache_mgr = get_cache_manager()
    cache_mgr.clear()
    
    owner1, repo1 = "owner1", "repo1"
    owner2, repo2 = "owner2", "repo2"
    repo_key1 = f"{owner1}/{repo1}"
    repo_key2 = f"{owner2}/{repo2}"
    
    key1 = get_repo_summary_key(owner1, repo1)
    key2 = get_repo_summary_key(owner2, repo2)
    
    # Write summary cache for both
    cache_mgr.set(key1, {"summary": "repo1"})
    cache_mgr.set(key2, {"summary": "repo2"})
    
    # Record starting generations
    start_gen1 = invalidation_tracker.get_generation(repo_key1)
    start_gen2 = invalidation_tracker.get_generation(repo_key2)
    
    # Invalidate repo1
    cache_mgr.invalidate_repository(owner1, repo1)
    
    # Verify repo1's keys are cleared, and generation is incremented
    assert cache_mgr.get(key1) is None
    assert invalidation_tracker.get_generation(repo_key1) == start_gen1 + 1
    
    # Verify repo2's keys and generation are completely untouched
    assert cache_mgr.get(key2) == {"summary": "repo2"}
    assert invalidation_tracker.get_generation(repo_key2) == start_gen2


def test_empty_repository_invalidation():
    """Verify that invalidating a repository that does not exist in the cache works gracefully."""
    cache_mgr = get_cache_manager()
    owner, repo = "empty-owner", "empty-repo"
    repo_key = f"{owner}/{repo}"
    
    start_gen = invalidation_tracker.get_generation(repo_key)
    
    # Trigger invalidation on empty repo
    try:
        cache_mgr.invalidate_repository(owner, repo)
    except Exception as exc:
        pytest.fail(f"invalidate_repository raised an unexpected exception: {exc}")
        
    # Verify generation is still incremented
    assert invalidation_tracker.get_generation(repo_key) == start_gen + 1
