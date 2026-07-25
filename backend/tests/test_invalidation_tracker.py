import time
import pytest
import threading
from concurrent.futures import ThreadPoolExecutor

from app.services.invalidation_tracker import InvalidationTracker, invalidation_tracker


def test_default_generation():
    """Verify that a repository has a default generation of 0."""
    tracker = InvalidationTracker()
    assert tracker.get_generation("mock-owner/mock-repo") == 0


def test_generation_increment():
    """Verify that repository generations increment correctly."""
    tracker = InvalidationTracker()
    repo = "pallets/flask"
    
    # 0 -> 1
    assert tracker.increment_generation(repo) == 1
    assert tracker.get_generation(repo) == 1
    
    # 1 -> 2
    assert tracker.increment_generation(repo) == 2
    assert tracker.get_generation(repo) == 2


def test_monotonic_behavior():
    """Verify that generation counts are strictly monotonic (never decrease)."""
    tracker = InvalidationTracker()
    repo = "fastapi/fastapi"
    
    gen1 = tracker.increment_generation(repo)
    gen2 = tracker.increment_generation(repo)
    gen3 = tracker.increment_generation(repo)
    
    assert gen1 < gen2 < gen3
    assert gen1 == 1
    assert gen2 == 2
    assert gen3 == 3


def test_thread_local_helpers():
    """Verify that thread-local generation helpers operate correctly on the current thread."""
    tracker = InvalidationTracker()
    
    # Defaults to None
    assert tracker.get_thread_generation() is None
    
    # Set and get
    tracker.set_thread_generation(42)
    assert tracker.get_thread_generation() == 42
    
    # Clear
    tracker.clear_thread_generation()
    assert tracker.get_thread_generation() is None


def test_worker_initialization():
    """Verify that worker initialization helper propagates context to spawned threads."""
    tracker = InvalidationTracker()
    
    def worker_target(parent_generation):
        # Initialize the worker context
        tracker.init_worker(parent_generation)
        return tracker.get_thread_generation()

    # If parent generation is 10, worker should receive 10
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker_target, 10)
        assert future.result() == 10
        
    # If parent generation is None, worker should receive None
    with ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(worker_target, None)
        assert future.result() is None


def test_pruning_behavior():
    """Verify that inactive entries are successfully pruned after the idle timeout."""
    # Set an idle timeout of 0.05 seconds for testing
    tracker = InvalidationTracker(idle_timeout_seconds=0.05)
    
    repo1 = "owner/repo1"
    repo2 = "owner/repo2"
    
    # Add repo1 to tracker (generation 1)
    tracker.increment_generation(repo1)
    assert tracker.get_generation(repo1) == 1
    
    # Wait for the entry to expire
    time.sleep(0.06)
    
    # Increment repo2. This should trigger pruning of repo1.
    tracker.increment_generation(repo2)
    
    # Verify repo2 is active and has generation 1
    assert tracker.get_generation(repo2) == 1
    
    # Verify repo1 has been pruned and returns default generation 0
    assert tracker.get_generation(repo1) == 0


def test_concurrent_generation_increments():
    """Verify that concurrent generation increments are thread-safe and correct."""
    tracker = InvalidationTracker()
    repo = "owner/concurrent-repo"
    
    num_threads = 50
    increments_per_thread = 10
    
    def run_increments():
        for _ in range(increments_per_thread):
            tracker.increment_generation(repo)
            
    threads = []
    for _ in range(num_threads):
        t = threading.Thread(target=run_increments)
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    # Final generation should be exactly num_threads * increments_per_thread
    expected_generation = num_threads * increments_per_thread
    assert tracker.get_generation(repo) == expected_generation


def test_singleton_instance():
    """Verify the global invalidation tracker singleton instance is exported and works."""
    assert invalidation_tracker is not None
    assert isinstance(invalidation_tracker, InvalidationTracker)
