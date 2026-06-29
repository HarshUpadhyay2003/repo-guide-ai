import logging
import time
import json
from typing import Any, Dict
from app.services.llm_service import LLMService
from app.utils.performance_utils import estimate_tokens
from constants import ENABLE_DEEP_PROFILING

# Cache imports
from app.core.cache.dependencies import get_cache_manager
from app.core.cache.manager import CacheManager
from app.core.cache.keys import get_repo_summary_key
from app.core.cache.config import CACHE_TTL_REPO_SUMMARY

logger = logging.getLogger(__name__)

class RepositorySummaryService:
    """Generate repository summaries and perform deep profiling."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        cache_manager: CacheManager | None = None
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.cache_manager = cache_manager or get_cache_manager()

    def generate_summary(self, metadata: Dict[str, Any], readme: str, contributing: str, prompt: str) -> Dict[str, Any]:
        """Generate repository summary with optional deep profiling diagnostics."""
        stage_start = time.perf_counter()
        start_time_sec = time.time()
        
        # 1. Cache Read Attempt
        owner = metadata.get("owner")
        repo = metadata.get("name") or metadata.get("repo")
        
        key = None
        cached_summary = None
        if owner and repo:
            try:
                key = get_repo_summary_key(owner, repo)
                cached_summary = self.cache_manager.get(key)
            except Exception as exc:
                if isinstance(exc, (TypeError, ValueError)):
                    raise
                logger.warning("[CACHE] Cache check failed for key %s: %s", key or "unknown", exc)
                
            if cached_summary is not None:
                print("[CACHE][Summary] HIT")
                
                # Save metrics to service context if available
                stage_dur = time.perf_counter() - stage_start
                if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                    self.metrics["summary_llm_generation"] = 0.0
                    self.metrics["summary_json_parse"] = 0.0
                    self.metrics["summary_schema_validation"] = 0.0
                    self.metrics["summary_total"] = stage_dur
                    
                return cached_summary
            else:
                print("[CACHE][Summary] MISS")
        
        system_prompt = (
            "You are a strict JSON generator. Reply with valid JSON only, "
            "without markdown fences, explanations, or commentary."
        )
        user_prompt = f"{prompt}\nReturn valid JSON only."

        # Perform the actual LLM call and measure timings
        llm_start = time.perf_counter()
        response = self.llm_service.client.chat.completions.create(
            model=self.llm_service.model,
            temperature=self.llm_service.temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            response_format={"type": "json_object"},
        )
        llm_end = time.perf_counter()
        content = response.choices[0].message.content or ""
        end_time_sec = time.time()

        generation_dur = llm_end - llm_start

        # Parse JSON
        parse_start = time.perf_counter()
        parsed = self.llm_service._extract_json(content)
        parse_end = time.perf_counter()

        parse_dur = parse_end - parse_start
        validation_dur = 0.0 # No Pydantic schema validation for summary
        stage_dur = time.perf_counter() - stage_start

        if ENABLE_DEEP_PROFILING:
            prompt_estimated_tokens = estimate_tokens(prompt)
            response_estimated_tokens = estimate_tokens(content)
            throughput = response_estimated_tokens / generation_dur if generation_dur > 0 else 0.0
            
            start_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(start_time_sec))
            end_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(end_time_sec))
            
            print()
            print("[LLM PROFILE] Repository Summary")
            print()
            print(f"README chars: {len(readme)}")
            print(f"CONTRIBUTING chars: {len(contributing)}")
            print()
            print(f"Prompt chars: {len(prompt)}")
            print(f"Prompt estimated tokens: {prompt_estimated_tokens}")
            print()
            print(f"Model: {self.llm_service.model}")
            print(f"Start Time: {start_str}")
            print(f"End Time: {end_str}")
            print()
            print(f"Generation Duration: {generation_dur:.2f}s")
            print()
            print(f"Response chars: {len(content)}")
            print(f"Response estimated tokens: {response_estimated_tokens}")
            print()
            print(f"Estimated Throughput: {throughput:.2f}")
            print()
            print(f"JSON Parse Time: {parse_dur:.4f}s")
            print(f"Schema Validation Time: {validation_dur:.4f}s")
            print(f"Total Summary Stage Time: {stage_dur:.2f}s")
            print()
            print("Top Context Contributors")
            print()
            print(f"README chars: {len(readme)}")
            print(f"CONTRIBUTING chars: {len(contributing)}")
            print(f"Repository Description chars: {len(metadata.get('description', ''))}")
            print()

        self.llm_service.token_manager.record_usage("Repository Summary", prompt, content)
        
        # Save metrics to service context if available
        if hasattr(self, "metrics") and isinstance(self.metrics, dict):
            self.metrics["summary_llm_generation"] = generation_dur
            self.metrics["summary_json_parse"] = parse_dur
            self.metrics["summary_schema_validation"] = validation_dur
            self.metrics["summary_total"] = stage_dur
            
        # Cache Write Attempt
        if owner and repo and key and parsed:
            try:
                self.cache_manager.set(key, parsed, CACHE_TTL_REPO_SUMMARY)
                print("[CACHE WRITE][Summary]")
            except Exception as exc:
                if isinstance(exc, (TypeError, ValueError)):
                    raise
                logger.warning("[CACHE] Cache write failed for key %s: %s", key, exc)

        return parsed
