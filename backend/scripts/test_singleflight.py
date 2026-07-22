import os
import sys
import time
import threading
from unittest.mock import MagicMock, patch

# Add backend root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient
from main import app
from app.services.singleflight_service import single_flight_coordinator
from app.core.cache.dependencies import get_cache_manager

def run_live_validation():
    print("====================================================")
    print("RUNNING LIVE SINGLE-FLIGHT CONCURRENCY VALIDATION")
    print("====================================================")
    
    analysis_calls = 0
    lock = threading.Lock()
    
    def mock_analyze_internal(self, url, mode="FAST_MVP"):
        nonlocal analysis_calls
        with lock:
            analysis_calls += 1
        print(f"[PROCESS] Thread {threading.current_thread().name} starting mock analysis for {url}...")
        time.sleep(0.5)
        
        from app.services.singleflight_service import normalize_repo_identity
        repo_key = normalize_repo_identity(url)
        owner, repo = repo_key.split("/")
        
        result = {
            "metadata": {"owner": owner, "repo": repo},
            "summary": {"tech_stack": ["Python"]},
            "repository_map": {},
            "issues": [],
            "roadmap": {}
        }
        
        try:
            from app.core.cache.keys import get_analysis_snapshot_key
            from app.core.cache.config import CACHE_TTL_ANALYSIS
            from app.services.singleflight_service import get_current_thread_flight, FlightState
            
            flight = get_current_thread_flight()
            if flight and flight.state == FlightState.TIMEOUT:
                print("[CACHE] Stale flight due to timeout. Skipping cache write.")
            else:
                analysis_key = get_analysis_snapshot_key(owner, repo)
                cache_mgr.set(analysis_key, result, ttl=CACHE_TTL_ANALYSIS)
                print(f"[CACHE] Wrote analysis result to cache for {owner}/{repo}.")
        except Exception as e:
            print(f"[CACHE] Failed to write to cache: {e}")
            
        return result
        
    client = TestClient(app)
    
    cache_mgr = get_cache_manager()
    with cache_mgr._stats_lock:
        cache_mgr._hits = 0
        cache_mgr._misses = 0
        cache_mgr._writes = 0
        cache_mgr._deletes = 0
        cache_mgr._lookup_time_ms = 0.0
        cache_mgr._write_time_ms = 0.0
    
    # Clean the cache for test repos
    try:
        from app.core.cache.keys import get_analysis_snapshot_key
        cache_mgr.delete(get_analysis_snapshot_key("mock", "mock-repo"))
        for i in range(10):
            cache_mgr.delete(get_analysis_snapshot_key("mock", f"repo{i}"))
    except Exception:
        pass
        
    single_flight_coordinator.reset_metrics()
    
    # Patch RepoService._analyze_repository_internal
    with patch("app.services.repo_service.RepoService._analyze_repository_internal", mock_analyze_internal):
        
        # --- SCENARIO A: 10 concurrent requests to the SAME repository ---
        print("\n--- SCENARIO A: 10 concurrent requests to the SAME repository ---")
        analysis_calls = 0
        single_flight_coordinator.reset_metrics()
        
        results = [None] * 10
        threads = []
        
        def call_api(idx):
            print(f"[REQUEST] Thread {idx} calling /repo/analyze...")
            response = client.post("/repo/analyze", json={"url": "https://github.com/mock/mock-repo"})
            results[idx] = response
            print(f"[RESPONSE] Thread {idx} completed with status {response.status_code}.")
            
        for i in range(10):
            t = threading.Thread(target=call_api, args=(i,), name=f"Worker-{i}")
            threads.append(t)
            t.start()
            time.sleep(0.01) # small stagger
            
        for t in threads:
            t.join()
            
        print("\n[VERIFICATION SCENARIO A]")
        print(f"Total API responses: {len(results)}")
        print(f"Total internal analysis executions: {analysis_calls}")
        assert all(r.status_code == 200 for r in results), "Not all requests returned 200"
        assert analysis_calls == 1, f"Expected exactly 1 internal execution, got {analysis_calls}"
        
        stats = cache_mgr.get_stats()
        print(f"Cache stats: {stats}")
        
        sf_metrics = single_flight_coordinator.get_metrics()
        print(f"Coordinator metrics: {sf_metrics}")
        assert sf_metrics["total_flights"] == 1
        assert sf_metrics["cache_reused_after_wait"] == 9
        
        # --- SCENARIO B: 10 concurrent requests to DIFFERENT repositories ---
        print("\n--- SCENARIO B: 10 concurrent requests to DIFFERENT repositories ---")
        analysis_calls = 0
        single_flight_coordinator.reset_metrics()
        
        results_b = [None] * 10
        threads_b = []
        
        def call_api_diff(idx):
            repo_url = f"https://github.com/mock/repo{idx}"
            print(f"[REQUEST] Thread {idx} calling /repo/analyze for repo{idx}...")
            response = client.post("/repo/analyze", json={"url": repo_url})
            results_b[idx] = response
            print(f"[RESPONSE] Thread {idx} completed for repo{idx} with status {response.status_code}.")
            
        for i in range(10):
            t = threading.Thread(target=call_api_diff, args=(i,), name=f"Worker-Diff-{i}")
            threads_b.append(t)
            t.start()
            
        for t in threads_b:
            t.join()
            
        print("\n[VERIFICATION SCENARIO B]")
        print(f"Total API responses: {len(results_b)}")
        print(f"Total internal analysis executions: {analysis_calls}")
        assert all(r.status_code == 200 for r in results_b), "Not all requests returned 200"
        assert analysis_calls == 10, f"Expected exactly 10 internal executions, got {analysis_calls}"
        
        sf_metrics_b = single_flight_coordinator.get_metrics()
        print(f"Coordinator metrics: {sf_metrics_b}")
        assert sf_metrics_b["total_flights"] == 10
        assert sf_metrics_b["cache_reused_after_wait"] == 0
        
        # --- SCENARIO C: Repeated identical repository requests (Cache reuse after completion) ---
        print("\n--- SCENARIO C: Repeated identical repository requests (Cache reuse) ---")
        analysis_calls = 0
        single_flight_coordinator.reset_metrics()
        
        print("[REQUEST] Calling /repo/analyze for mock/mock-repo...")
        response1 = client.post("/repo/analyze", json={"url": "https://github.com/mock/mock-repo"})
        print(f"[RESPONSE] Completed with status {response1.status_code}")
        
        print("[REQUEST] Calling /repo/analyze for mock/mock-repo again...")
        response2 = client.post("/repo/analyze", json={"url": "https://github.com/mock/mock-repo"})
        print(f"[RESPONSE] Completed with status {response2.status_code}")
        
        print("\n[VERIFICATION SCENARIO C]")
        print(f"Total internal analysis executions: {analysis_calls}")
        assert response1.status_code == 200 and response2.status_code == 200
        assert analysis_calls == 0, f"Expected 0 internal executions (cache hit), got {analysis_calls}"
        
        sf_metrics_c = single_flight_coordinator.get_metrics()
        print(f"Coordinator metrics: {sf_metrics_c}")
        assert sf_metrics_c["total_flights"] == 0
        
    print("\n====================================================")
    print("LIVE VALIDATION COMPLETED SUCCESSFULLY!")
    print("====================================================")

if __name__ == "__main__":
    run_live_validation()
