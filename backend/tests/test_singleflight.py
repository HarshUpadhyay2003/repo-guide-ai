import time
import pytest
import threading
from unittest.mock import MagicMock, patch
from typing import Dict, Any

from app.services.singleflight_service import (
    SingleFlightCoordinator,
    normalize_repo_identity,
    FlightState,
    single_flight_coordinator,
    get_current_thread_flight
)
from app.services.repo_service import RepoService
from app.core.cache.dependencies import get_cache_manager

# 1. Normalization tests
def test_repository_normalization():
    assert normalize_repo_identity("https://github.com/pallets/flask") == "pallets/flask"
    assert normalize_repo_identity("https://github.com/Pallets/Flask.git") == "pallets/flask"
    assert normalize_repo_identity("https://github.com/fastapi/fastapi/") == "fastapi/fastapi"
    assert normalize_repo_identity("Pallets/Flask") == "pallets/flask"
    assert normalize_repo_identity("pallets/flask.git") == "pallets/flask"
    with pytest.raises(ValueError):
        normalize_repo_identity("invalid_repo_name")

# 2. Concurrent Requests (Same Repo) -> Exactly one execution
def test_concurrent_requests_same_repo():
    coordinator = SingleFlightCoordinator()
    execution_count = 0
    execution_started = threading.Event()
    execution_continue = threading.Event()
    
    def slow_compute():
        nonlocal execution_count
        execution_count += 1
        execution_started.set()
        execution_continue.wait(timeout=5.0)
        return {"data": "ok"}
        
    results = []
    def run_request():
        res = coordinator.execute("https://github.com/test-owner/test-repo", slow_compute)
        results.append(res)
        
    t1 = threading.Thread(target=run_request)
    t2 = threading.Thread(target=run_request)
    
    t1.start()
    assert execution_started.wait(timeout=5.0)
    
    t2.start()
    time.sleep(0.05)
    
    execution_continue.set()
    
    t1.join()
    t2.join()
    
    assert execution_count == 1
    assert len(results) == 2
    assert results[0] == {"data": "ok"}
    assert results[1] == {"data": "ok"}
    
    metrics = coordinator.get_metrics()
    assert metrics["total_flights"] == 1
    assert metrics["completed_flights"] == 1
    assert metrics["cache_reused_after_wait"] == 1

# 3. Concurrent Requests (Different Repos) -> Parallel execution
def test_concurrent_requests_different_repos():
    coordinator = SingleFlightCoordinator()
    execution_count = 0
    lock = threading.Lock()
    
    def compute_repo():
        nonlocal execution_count
        with lock:
            execution_count += 1
        time.sleep(0.05)
        return {"data": "ok"}
        
    t1 = threading.Thread(target=coordinator.execute, args=("https://github.com/owner/repo1", compute_repo))
    t2 = threading.Thread(target=coordinator.execute, args=("https://github.com/owner/repo2", compute_repo))
    
    t1.start()
    t2.start()
    
    t1.join()
    t2.join()
    
    assert execution_count == 2
    metrics = coordinator.get_metrics()
    assert metrics["total_flights"] == 2
    assert metrics["completed_flights"] == 2

# 4. Flight released after success
def test_flight_released_after_success():
    coordinator = SingleFlightCoordinator()
    res = coordinator.execute("https://github.com/owner/repo", lambda: {"status": "success"})
    assert res == {"status": "success"}
    assert len(coordinator.active_flights) == 0
    assert coordinator.get_metrics()["completed_flights"] == 1

# 5. Flight released after exception & failure propagation
def test_flight_released_after_exception():
    coordinator = SingleFlightCoordinator()
    
    def raise_err():
        raise ValueError("simulated failure")
        
    with pytest.raises(ValueError, match="simulated failure"):
        coordinator.execute("https://github.com/owner/repo", raise_err)
        
    assert len(coordinator.active_flights) == 0
    assert coordinator.get_metrics()["failed_flights"] == 1

# 6. Retry after failure creates new flight
def test_retry_after_failure():
    coordinator = SingleFlightCoordinator()
    call_count = 0
    
    def flaky_compute():
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            raise RuntimeError("first try fail")
        return {"try": call_count}
        
    with pytest.raises(RuntimeError, match="first try fail"):
        coordinator.execute("https://github.com/owner/repo", flaky_compute)
        
    res = coordinator.execute("https://github.com/owner/repo", flaky_compute)
    assert res == {"try": 2}
    assert call_count == 2
    metrics = coordinator.get_metrics()
    assert metrics["failed_flights"] == 1
    assert metrics["completed_flights"] == 1

# 7. Timeout cleanup and stale cache prevention
def test_execution_timeout_cleanup():
    coordinator = SingleFlightCoordinator(default_timeout=0.05)
    
    def slow_func():
        time.sleep(0.1)
        return {"data": "slow"}
        
    with pytest.raises(TimeoutError):
        coordinator.execute("https://github.com/owner/repo", slow_func)
        
    metrics = coordinator.get_metrics()
    assert metrics["timeout_flights"] == 1
    assert len(coordinator.active_flights) == 0

# 8. No duplicate cache writes on RepoService
@patch("app.core.cache.dependencies.get_cache_manager")
def test_no_duplicate_cache_writes(mock_get_cache_manager):
    mock_cache = MagicMock()
    mock_cache.get_analysis.return_value = None
    mock_get_cache_manager.return_value = mock_cache
    
    service = RepoService()
    service._analyze_repository_internal = MagicMock(return_value={"data": "mock"})
    
    single_flight_coordinator.reset_metrics()
    
    # We will coordinate t1 and t2 to run concurrently
    execution_started = threading.Event()
    execution_continue = threading.Event()
    
    def mock_internal(url, mode="FAST_MVP"):
        execution_started.set()
        execution_continue.wait(timeout=5.0)
        mock_cache.set("repo:mock-owner:mock-repo:snapshot", {"data": "mock"}, ttl=60)
        return {"data": "mock"}
        
    service._analyze_repository_internal.side_effect = mock_internal
    
    def run_analyze():
        service.analyze_repository("https://github.com/mock-owner/mock-repo")
        
    t1 = threading.Thread(target=run_analyze)
    t2 = threading.Thread(target=run_analyze)
    
    t1.start()
    assert execution_started.wait(timeout=5.0)
    
    t2.start()
    time.sleep(0.05)
    
    execution_continue.set()
    
    t1.join()
    t2.join()
    
    service._analyze_repository_internal.assert_called_once()
    assert mock_cache.set.call_count == 1
    metrics = single_flight_coordinator.get_metrics()
    assert metrics["total_flights"] == 1
    assert metrics["cache_reused_after_wait"] == 1

# 9. Cache already populated bypasses coordinator
@patch("app.core.cache.dependencies.get_cache_manager")
def test_cache_populated_bypasses_coordinator(mock_get_cache_manager):
    mock_cache = MagicMock()
    mock_cache.get_analysis.return_value = {"cached": "data"}
    mock_get_cache_manager.return_value = mock_cache
    
    service = RepoService()
    service._analyze_repository_internal = MagicMock()
    
    single_flight_coordinator.reset_metrics()
    
    res = service.analyze_repository("https://github.com/mock-owner/mock-repo")
    assert res == {"cached": "data"}
    service._analyze_repository_internal.assert_not_called()
    
    metrics = single_flight_coordinator.get_metrics()
    assert metrics["total_flights"] == 0

# 10. Stress test: 20 concurrent same repo
def test_stress_20_same_repo():
    coordinator = SingleFlightCoordinator()
    execution_count = 0
    execution_started = threading.Event()
    execution_continue = threading.Event()
    
    def slow_compute():
        nonlocal execution_count
        execution_count += 1
        execution_started.set()
        execution_continue.wait(timeout=5.0)
        return {"data": "stress"}
        
    results = [None] * 20
    threads = []
    
    def run_request(idx):
        res = coordinator.execute("https://github.com/owner/repo", slow_compute)
        results[idx] = res
        
    t_owner = threading.Thread(target=run_request, args=(0,))
    threads.append(t_owner)
    t_owner.start()
    
    assert execution_started.wait(timeout=5.0)
    
    for i in range(1, 20):
        t = threading.Thread(target=run_request, args=(i,))
        threads.append(t)
        t.start()
        
    time.sleep(0.05)
    execution_continue.set()
    
    for t in threads:
        t.join()
        
    assert execution_count == 1
    assert all(r == {"data": "stress"} for r in results)
    metrics = coordinator.get_metrics()
    assert metrics["total_flights"] == 1
    assert metrics["cache_reused_after_wait"] == 19

# 11. Stress test: 20 concurrent different repos
def test_stress_20_different_repos():
    coordinator = SingleFlightCoordinator()
    execution_count = 0
    lock = threading.Lock()
    
    def compute_repo():
        nonlocal execution_count
        with lock:
            execution_count += 1
        time.sleep(0.02)
        return {"data": "stress"}
        
    threads = []
    for i in range(20):
        t = threading.Thread(
            target=coordinator.execute,
            args=(f"https://github.com/owner/repo{i}", compute_repo)
        )
        threads.append(t)
        t.start()
        
    for t in threads:
        t.join()
        
    assert execution_count == 20
    metrics = coordinator.get_metrics()
    assert metrics["total_flights"] == 20
    assert metrics["completed_flights"] == 20

# 12. Slow producer and fast waiter joins
def test_slow_producer_fast_waiter():
    coordinator = SingleFlightCoordinator()
    producer_started = threading.Event()
    
    def slow_compute():
        producer_started.set()
        time.sleep(0.1)
        return {"data": "slow_producer"}
        
    res_list = []
    
    def run_waiter():
        producer_started.wait()
        time.sleep(0.01)
        res = coordinator.execute("https://github.com/owner/repo", lambda: {"data": "waiter"})
        res_list.append(res)
        
    t_waiter = threading.Thread(target=run_waiter)
    t_waiter.start()
    
    res_producer = coordinator.execute("https://github.com/owner/repo", slow_compute)
    t_waiter.join()
    
    assert res_producer == {"data": "slow_producer"}
    assert len(res_list) == 1
    assert res_list[0] == {"data": "slow_producer"}
    
    metrics = coordinator.get_metrics()
    assert metrics["total_flights"] == 1
    assert metrics["cache_reused_after_wait"] == 1


# 13. Configurable timeout loading
def test_configurable_timeout_loading():
    with patch("app.core.config.settings.SINGLEFLIGHT_TIMEOUT_SECONDS", 42):
        coordinator = SingleFlightCoordinator()
        assert coordinator.default_timeout == 42.0

# 14. Stats output verification
def test_stats_output():
    coordinator = SingleFlightCoordinator()
    res = coordinator.execute("https://github.com/owner/repo", lambda: {"status": "ok"})
    assert res == {"status": "ok"}
    
    stats = coordinator.stats()
    assert stats["active_flights"] == 0
    assert stats["completed_flights"] == 1
    assert stats["failed_flights"] == 0
    assert stats["timeout_flights"] == 0
    assert stats["cache_reused_after_wait"] == 0
    assert stats["average_wait_time"] == 0.0
    assert stats["peak_waiters"] == 0

# 15. Snapshot output verification
def test_snapshot_output():
    coordinator = SingleFlightCoordinator()
    execution_started = threading.Event()
    execution_continue = threading.Event()
    
    def slow_func():
        execution_started.set()
        execution_continue.wait(timeout=5.0)
        return {"status": "ok"}
        
    def run_flight():
        coordinator.execute("https://github.com/owner/repo", slow_func)
        
    t = threading.Thread(target=run_flight)
    t.start()
    
    assert execution_started.wait(timeout=5.0)
    
    snapshot = coordinator.snapshot()
    assert snapshot["active_flights"] == 1
    assert len(snapshot["repositories"]) == 1
    repo_snap = snapshot["repositories"][0]
    assert repo_snap["repository"] == "owner/repo"
    assert repo_snap["state"] == "RUNNING"
    assert repo_snap["waiters"] == 0
    assert repo_snap["flight_id"].startswith("f_")
    assert repo_snap["elapsed_seconds"] >= 0.0
    
    execution_continue.set()
    t.join()
    
    snapshot_after = coordinator.snapshot()
    assert snapshot_after["active_flights"] == 0
    assert len(snapshot_after["repositories"]) == 0

