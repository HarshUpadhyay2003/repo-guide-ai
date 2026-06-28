import logging
import time
import json
from typing import Any, Dict
from app.services.llm_service import LLMService
from app.utils.performance_utils import estimate_tokens
from constants import ENABLE_DEEP_PROFILING

logger = logging.getLogger(__name__)

class RepositorySummaryService:
    """Generate repository summaries and perform deep profiling."""

    def __init__(self, llm_service: LLMService | None = None) -> None:
        self.llm_service = llm_service or LLMService()

    def generate_summary(self, metadata: Dict[str, Any], readme: str, contributing: str, prompt: str) -> Dict[str, Any]:
        """Generate repository summary with optional deep profiling diagnostics."""
        stage_start = time.perf_counter()
        start_time_sec = time.time()
        
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
            
        return parsed
