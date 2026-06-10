import logging
import time
from contextlib import contextmanager
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

def estimate_tokens(text: str) -> int:
    """Rough estimation: 1 token ~= 4 characters."""
    return len(str(text)) // 4

class PerformanceTracker:
    def __init__(self) -> None:
        self.operations: List[Dict[str, Any]] = []
        self.issues: Dict[str, Dict[str, float]] = {}
        self.start_time = time.perf_counter()

    def record(self, name: str, duration: float, category: str = "SERVICE", issue_number: Optional[str] = None) -> None:
        if issue_number:
            if issue_number not in self.issues:
                self.issues[issue_number] = {}
            self.issues[issue_number][name] = duration
        else:
            self.operations.append({"name": name, "duration": duration, "category": category})
            
        logger.info("[%s PERF] %s: %.2fs", category, name, duration)
        if duration > 5.0:
            logger.warning("[WARNING] %s exceeded threshold. Duration: %.2fs", name, duration)

    def generate_report(self) -> str:
        total = time.perf_counter() - self.start_time
        lines = [
            "",
            "===================================",
            "FULL ANALYSIS PERFORMANCE REPORT",
            "==================================="
        ]
        for op in self.operations:
            name = op["name"] + ":"
            lines.append(f"{name.ljust(25)} {op['duration']:.2f}s")
            
        if self.issues:
            for issue_num, metrics in self.issues.items():
                lines.append(f"\nIssue #{issue_num}:")
                for m_name, m_dur in metrics.items():
                    name = m_name + ":"
                    lines.append(f"{name.ljust(25)} {m_dur:.2f}s")
                    
        lines.append("")
        lines.append(f"{'TOTAL:'.ljust(25)} {total:.2f}s")
        lines.append("===================================")
        return "\n".join(lines)

@contextmanager
def timed_operation(name: str, category: str = "SERVICE", tracker: Optional[PerformanceTracker] = None, issue_number: Optional[str] = None):
    start = time.perf_counter()
    yield
    duration = time.perf_counter() - start
    if tracker:
        tracker.record(name, duration, category, issue_number)
    else:
        logger.info("[%s PERF] %s: %.2fs", category, name, duration)
        if duration > 5.0:
            logger.warning("[WARNING] %s exceeded threshold. Duration: %.2fs", name, duration)
