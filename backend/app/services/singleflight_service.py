import uuid
import time
import logging
import threading
from enum import Enum
from typing import Dict, Any, Callable, Optional, List

logger = logging.getLogger(__name__)

class FlightState(str, Enum):
    RUNNING = "RUNNING"
    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"

class Flight:
    def __init__(self, repository_key: str, deadline: float):
        self.flight_id = f"f_{uuid.uuid4().hex[:6]}"
        self.repository_key = repository_key
        self.state = FlightState.RUNNING
        self.started_at = time.perf_counter()
        self.finished_at: Optional[float] = None
        self.deadline = deadline
        self.waiters_count = 0
        self.lock = threading.RLock()
        self.condition = threading.Condition(self.lock)
        self.result: Optional[Dict[str, Any]] = None
        self.exception: Optional[Exception] = None
        self.metrics: Optional[Dict[str, Any]] = None

_thread_local = threading.local()

def get_current_thread_flight() -> Optional[Flight]:
    return getattr(_thread_local, "current_flight", None)

def log_coordinator(
    level: int,
    msg: str,
    flight: Optional[Flight] = None,
    repo_key: Optional[str] = None,
    elapsed: Optional[float] = None,
    *args
) -> None:
    """Format and log coordinator events consistently.
    
    Format:
    [Flight=ID]
    Repo=key
    Thread=name
    [Elapsed=X.XXs]
    State=state
    Message=msg
    """
    flight_id = flight.flight_id if flight else "N/A"
    repo = repo_key or (flight.repository_key if flight else "N/A")
    state = (flight.state.value if isinstance(flight.state, Enum) else str(flight.state)) if flight else "N/A"
    thread_name = threading.current_thread().name
    
    elapsed_str = f"\nElapsed={elapsed:.2f}s" if elapsed is not None else ""
    log_msg = f"[Flight={flight_id}]\nRepo={repo}\nThread={thread_name}{elapsed_str}\nState={state}\nMessage={msg}"
    logger.log(level, log_msg, *args)

def normalize_repo_identity(url_or_identity: str) -> str:
    """Normalize a GitHub repository URL or owner/repo string to a canonical lowercase 'owner/repo' format."""
    if not isinstance(url_or_identity, str) or not url_or_identity.strip():
        raise ValueError("Repository identifier must be a non-empty string.")
        
    val = url_or_identity.strip()
    from app.utils.url_validation import validate_github_url
    
    if "/" in val and not val.startswith("http://") and not val.startswith("https://"):
        full_url = f"https://github.com/{val}"
        owner, repo = validate_github_url(full_url)
    else:
        owner, repo = validate_github_url(val)
        
    return f"{owner}/{repo}"

class SingleFlightCoordinator:
    def __init__(self, default_timeout: Optional[float] = None):
        self.lock = threading.Lock()
        self.active_flights: Dict[str, Flight] = {}
        
        # Load configurable timeout: Environment Variable -> Config -> Default (180s)
        if default_timeout is None:
            try:
                from app.core.config import settings
                default_timeout = float(settings.SINGLEFLIGHT_TIMEOUT_SECONDS)
            except Exception:
                default_timeout = 180.0
        self.default_timeout = default_timeout
        
        # Diagnostics metrics
        self.total_flights = 0
        self.completed_flights = 0
        self.failed_flights = 0
        self.timeout_flights = 0
        self.cache_reused_after_wait = 0
        self.total_wait_time = 0.0
        self.wait_count = 0
        self.peak_waiters = 0

    def execute(
        self,
        url: str,
        func: Callable[[], Any],
        timeout_seconds: Optional[float] = None,
        service_instance: Optional[Any] = None
    ) -> Any:
        repo_key = normalize_repo_identity(url)
        log_coordinator(logging.INFO, "Repository normalized", repo_key=repo_key)
        
        effective_timeout = timeout_seconds if timeout_seconds is not None else self.default_timeout
        now = time.perf_counter()
        deadline = now + effective_timeout
        
        flight = None
        is_owner = False
        wait_start = 0.0
        
        with self.lock:
            # Check if there is an active flight
            if repo_key in self.active_flights:
                flight = self.active_flights[repo_key]
                # Check if the active flight has already timed out but hasn't been cleaned up yet
                if time.perf_counter() >= flight.deadline and flight.state == FlightState.RUNNING:
                    log_coordinator(logging.WARNING, "Flight timed out before start. Cleaning up and starting fresh.", flight=flight)
                    flight.state = FlightState.TIMEOUT
                    self.timeout_flights += 1
                    with flight.condition:
                        flight.condition.notify_all()
                    del self.active_flights[repo_key]
                    flight = None
                    
            if flight is not None:
                # Join existing flight as a waiter
                flight.waiters_count += 1
                if flight.waiters_count > self.peak_waiters:
                    self.peak_waiters = flight.waiters_count
                is_owner = False
                wait_start = time.perf_counter()
                log_coordinator(logging.INFO, "Execution already running. Wait started", flight=flight)
            else:
                # Double Cache Lookup (check cache before creating flight under coordinator lock)
                try:
                    from app.core.cache.dependencies import get_cache_manager
                    cache_mgr = get_cache_manager()
                    owner, repo = repo_key.split("/")
                    cached_result = cache_mgr.get_analysis(owner, repo)
                    if cached_result is not None:
                        log_coordinator(logging.INFO, "Cache hit on double-check inside coordinator", repo_key=repo_key)
                        self.cache_reused_after_wait += 1
                        return cached_result
                except Exception as e:
                    log_coordinator(logging.WARNING, f"Cache lookup failed inside coordinator: {e}", repo_key=repo_key)
                
                # Create a new flight
                flight = Flight(repo_key, deadline)
                self.active_flights[repo_key] = flight
                self.total_flights += 1
                is_owner = True
                log_coordinator(logging.INFO, "Flight created. Flight acquired", flight=flight)
                
        if is_owner:
            _thread_local.current_flight = flight
            try:
                # Check if deadline is already past
                if time.perf_counter() >= flight.deadline:
                    raise TimeoutError(f"Flight {flight.flight_id} timed out before starting execution.")
                    
                # Run the actual pipeline
                result = func()
                
                # Check for timeout during execution
                if time.perf_counter() >= flight.deadline:
                    raise TimeoutError(f"Flight {flight.flight_id} execution exceeded timeout limit.")
                
                # Complete the flight
                with flight.lock:
                    if flight.state == FlightState.RUNNING:
                        flight.state = FlightState.SUCCESS
                        flight.result = result
                        flight.finished_at = time.perf_counter()
                        if service_instance and hasattr(service_instance, "metrics"):
                            flight.metrics = service_instance.metrics
                        log_coordinator(logging.INFO, "Flight completed successfully", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                        
            except Exception as exc:
                with flight.lock:
                    if flight.state == FlightState.RUNNING:
                        if isinstance(exc, TimeoutError):
                            flight.state = FlightState.TIMEOUT
                            self.timeout_flights += 1
                            log_coordinator(logging.WARNING, "Flight timed out during execution", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                        else:
                            flight.state = FlightState.FAILED
                            flight.exception = exc
                            self.failed_flights += 1
                            log_coordinator(logging.ERROR, f"Flight failed: {exc}", flight=flight, elapsed=time.perf_counter() - flight.started_at)
            finally:
                _thread_local.current_flight = None
                with flight.condition:
                    # Notify all waiters
                    flight.condition.notify_all()
                
                # Remove from active flights under coordinator lock
                with self.lock:
                    if self.active_flights.get(repo_key) is flight:
                        del self.active_flights[repo_key]
                        log_coordinator(logging.INFO, "Flight released and removed from active flights", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                    
                    if flight.state == FlightState.SUCCESS:
                        self.completed_flights += 1
                        
                log_coordinator(logging.INFO, "Cleanup completed", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                
                # If failed, propagate the exception
                if flight.state == FlightState.FAILED:
                    raise flight.exception
                elif flight.state == FlightState.TIMEOUT:
                    raise TimeoutError(f"Analysis of repository {repo_key} timed out.")
                    
                return flight.result
        else:
            # Waiter path
            with flight.lock:
                while flight.state == FlightState.RUNNING:
                    remaining = flight.deadline - time.perf_counter()
                    if remaining <= 0:
                        break
                    
                    notified = flight.condition.wait(timeout=remaining)
                    if not notified:
                        break
            
            # Post-wait processing
            wait_dur = time.perf_counter() - wait_start
            self.total_wait_time += wait_dur
            self.wait_count += 1
            log_coordinator(logging.INFO, "Wait finished", flight=flight, elapsed=wait_dur)
            
            is_running = False
            with flight.lock:
                flight.waiters_count -= 1
                if flight.state == FlightState.RUNNING:
                    is_running = True
                    
            if is_running:
                log_coordinator(logging.WARNING, "Waiter timed out waiting for flight completion", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                with self.lock:
                    if self.active_flights.get(repo_key) is flight:
                        del self.active_flights[repo_key]
                with flight.lock:
                    if flight.state == FlightState.RUNNING:
                        flight.state = FlightState.TIMEOUT
                        self.timeout_flights += 1
                        with flight.condition:
                            flight.condition.notify_all()
                raise TimeoutError(f"Wait for analysis of repository {repo_key} timed out.")
                
            with flight.lock:
                if flight.state == FlightState.TIMEOUT:
                    log_coordinator(logging.WARNING, "Waiter received timeout notification", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                    raise TimeoutError(f"Analysis of repository {repo_key} timed out.")
                    
                if flight.state == FlightState.FAILED:
                    log_coordinator(logging.INFO, "Waiter receiving propagated failure", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                    raise flight.exception
                    
                if flight.state == FlightState.SUCCESS:
                    if service_instance and flight.metrics:
                        service_instance.metrics = flight.metrics
                    
                    self.cache_reused_after_wait += 1
                    log_coordinator(logging.INFO, "Waiter successfully received completed result. Cache reused", flight=flight, elapsed=time.perf_counter() - flight.started_at)
                    return flight.result
                    
            raise RuntimeError("Flight is in an invalid state.")

    def stats(self) -> Dict[str, Any]:
        with self.lock:
            avg_wait = self.total_wait_time / self.wait_count if self.wait_count > 0 else 0.0
            return {
                "active_flights": len(self.active_flights),
                "completed_flights": self.completed_flights,
                "failed_flights": self.failed_flights,
                "timeout_flights": self.timeout_flights,
                "cache_reused_after_wait": self.cache_reused_after_wait,
                "average_wait_time": avg_wait,
                "peak_waiters": self.peak_waiters,
            }

    def snapshot(self) -> Dict[str, Any]:
        with self.lock:
            repos_info = []
            for repo_key, flight in list(self.active_flights.items()):
                with flight.lock:
                    repos_info.append({
                        "repository": flight.repository_key,
                        "flight_id": flight.flight_id,
                        "state": flight.state.value if isinstance(flight.state, Enum) else str(flight.state),
                        "elapsed_seconds": round(time.perf_counter() - flight.started_at, 2),
                        "waiters": flight.waiters_count
                    })
            return {
                "active_flights": len(self.active_flights),
                "repositories": repos_info
            }

    def get_metrics(self) -> Dict[str, Any]:
        avg_wait = self.total_wait_time / self.wait_count if self.wait_count > 0 else 0.0
        return {
            "total_flights": self.total_flights,
            "completed_flights": self.completed_flights,
            "failed_flights": self.failed_flights,
            "timeout_flights": self.timeout_flights,
            "cache_reused_after_wait": self.cache_reused_after_wait,
            "average_wait_time": avg_wait,
            "peak_waiters": self.peak_waiters,
        }

    def reset_metrics(self) -> None:
        with self.lock:
            self.total_flights = 0
            self.completed_flights = 0
            self.failed_flights = 0
            self.timeout_flights = 0
            self.cache_reused_after_wait = 0
            self.total_wait_time = 0.0
            self.wait_count = 0
            self.peak_waiters = 0

# Global single-flight coordinator instance
single_flight_coordinator = SingleFlightCoordinator()
