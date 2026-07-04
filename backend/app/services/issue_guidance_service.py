import json
import logging
import time
import re
import os
from typing import Any, Dict, List

from app.schema.issue_guidance import IssueGuidanceInput, IssueGuidanceOutput
from app.services.llm_service import LLMGenerationError, LLMService
from app.utils.file_ranking import score_file, get_candidate_files
from constants import ENABLE_PERF_DIAGNOSTICS
from app.utils.performance_utils import estimate_tokens

logger = logging.getLogger(__name__)

COMPRESSED_GUIDANCE_PROMPT_TEMPLATE = """Analyze this GitHub issue and suggest exploration hints for a beginner contributor.

Repository Context: {repo_name} - {repo_desc}

{repo_summary}
{repository_map}
{readme}
{contributing}
Issue Title: {title}
Labels: {labels}

{body}
{comments}
{instructions}

Return ONLY valid JSON matching the exact schema below.

EXPECTED JSON SCHEMA:
{json_schema}"""

COMPRESSED_GUIDANCE_PROMPT_INSTRUCTIONS = """Instructions for generating each JSON field:
1. "analysis":
   - "beginner_explanation": Explain the issue simply for a beginner.
   - "skills_required": List of required skills (e.g. Python, React).
   - "affected_area": Module or layout area affected.
   - "difficulty": Must be "Beginner", "Intermediate", or "Advanced".
   - "confidence_score": Confidence score from 0 to 100.
2. "exploration_hints":
   - "affected_area": Module or layout area affected.
   - "likely_directories": Most likely directories (CRITICAL: Must be selected from Candidate Directories).
   - "possible_files": Possible files to explore (CRITICAL: Must be selected from Candidate Files. Never invent or guess file names).
   - "reasoning": Explain why these are relevant.
   - "confidence": Confidence score from 0 to 100."""

COMPRESSED_GUIDANCE_PROMPT_SCHEMA = """{{
  "analysis": {{
    "beginner_explanation": "String",
    "skills_required": ["String", "String"],
    "affected_area": "String",
    "difficulty": "Beginner | Intermediate | Advanced",
    "confidence_score": Integer
  }},
  "exploration_hints": {{
    "affected_area": "String",
    "likely_directories": ["String", "String"],
    "possible_files": ["String", "String"],
    "reasoning": "String",
    "confidence": Integer
  }}
}}"""

# Keep old constant for backward compatibility
COMPRESSED_GUIDANCE_PROMPT = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE

# Cache imports
from app.core.cache.dependencies import get_cache_manager
from app.core.cache.manager import CacheManager
from app.core.cache.keys import get_issue_guidance_key
from app.core.cache.config import CACHE_TTL_ISSUE_GUIDANCE

def compress_markdown(text: str, keep_keywords: list, remove_keywords: list) -> str:
    """Perform semantic compression on markdown files (README / CONTRIBUTING)."""
    if not text:
        return ""
    
    # 1. Strip HTML comments/tags
    text = re.sub(r"<!--.*?-->", "", text, flags=re.DOTALL)
    text = re.sub(r"<[^>]+>", "", text)
    
    # 2. Omit large code blocks
    def code_replacer(match):
        code_content = match.group(2)
        if len(code_content.splitlines()) > 5 or len(code_content) > 200:
            return "```\n[Code block omitted for brevity]\n```"
        return match.group(0)
    
    text = re.sub(r"```(python|javascript|typescript|bash|sh|json|yaml|yml|html|css)?\n(.*?)\n```", code_replacer, text, flags=re.DOTALL | re.IGNORECASE)
    
    # 3. Split by headers
    lines = text.splitlines()
    sections = []
    current_header = "Intro"
    current_content = []
    
    for line in lines:
        if line.strip().startswith(("#", "##", "###", "####")):
            if current_content:
                sections.append((current_header, "\n".join(current_content)))
            current_header = line.strip()
            current_content = []
        else:
            current_content.append(line)
    if current_content:
        sections.append((current_header, "\n".join(current_content)))
        
    # 4. Filter sections
    filtered_sections = []
    for header, content in sections:
        header_lower = header.lower()
        if any(kw in header_lower for kw in remove_keywords):
            continue
        if keep_keywords:
            if "intro" in header_lower or header == "Intro" or any(kw in header_lower for kw in keep_keywords):
                filtered_sections.append(f"{header}\n{content}")
        else:
            filtered_sections.append(f"{header}\n{content}")
            
    return "\n\n".join(filtered_sections)

def compress_comments(comments: list) -> str:
    """Clean and filter issue comments to preserve only useful telemetry."""
    if not comments:
        return "None"
        
    cleaned_comments = []
    discard_patterns = [
        r"^\s*\+1\s*$",
        r"^\s*thanks\s*$",
        r"^\s*thank you\s*$",
        r"^\s*me too\s*$",
        r"^\s*lgtm\s*$",
        r"^\s*:+1:\s*$",
        r"^\s*bump\s*$"
    ]
    
    for c in comments:
        body = c.get("body", "")
        if not body:
            continue
            
        body_lower = body.strip().lower()
        if any(re.match(p, body_lower) for p in discard_patterns):
            continue
            
        if len(body_lower) < 10 and not any(char.isalnum() for char in body_lower):
            continue
            
        author = c.get("author") or c.get("user", {}).get("login", "User")
        cleaned_body = body[:300].strip() + ("..." if len(body) > 300 else "")
        cleaned_comments.append(f"@{author}: {cleaned_body}")
        
    if not cleaned_comments:
        return "None"
        
    return "\n".join(cleaned_comments)

class IssueGuidanceService:
    """Analyze GitHub issues and generate exploration hints in a single LLM request."""

    def __init__(
        self,
        llm_service: LLMService | None = None,
        cache_manager: CacheManager | None = None
    ) -> None:
        self.llm_service = llm_service or LLMService()
        self.cache_manager = cache_manager or get_cache_manager()

    def normalize_guidance_response(self, data: Dict[str, Any], fallback_affected_area: str = "Unknown Area") -> Dict[str, Any]:
        """Repairs common schema deviations before Pydantic validation."""
        # Normalize the "analysis" sub-object
        analysis = data.get("analysis", {})
        if not isinstance(analysis, dict):
            analysis = {}
            data["analysis"] = analysis
            
        if "beginner_explanation" not in analysis:
            if "explanation" in analysis:
                analysis["beginner_explanation"] = analysis.pop("explanation")
            elif "beginner_friendly_explanation" in analysis:
                analysis["beginner_friendly_explanation"] = analysis.pop("beginner_friendly_explanation")
            else:
                analysis["beginner_explanation"] = "No explanation provided."

        if "affected_area" in analysis and isinstance(analysis["affected_area"], list):
            analysis["affected_area"] = " ".join(str(x) for x in analysis["affected_area"])
        elif "affected_area" not in analysis:
            analysis["affected_area"] = fallback_affected_area

        if "confidence_score" in analysis and isinstance(analysis["confidence_score"], str):
            score_str = analysis["confidence_score"].strip().lower()
            if score_str == "low":
                analysis["confidence_score"] = 40
            elif score_str == "medium":
                analysis["confidence_score"] = 70
            elif score_str == "high":
                analysis["confidence_score"] = 90
            else:
                analysis["confidence_score"] = 50
        elif "confidence_score" not in analysis:
            analysis["confidence_score"] = 50

        if "skills_required" not in analysis:
            analysis["skills_required"] = []
        if "difficulty" not in analysis:
            analysis["difficulty"] = "Beginner"

        # Normalize the "exploration_hints" sub-object
        hints = data.get("exploration_hints", {})
        if not isinstance(hints, dict):
            hints = {}
            data["exploration_hints"] = hints

        if "affected_area" not in hints:
            hints["affected_area"] = fallback_affected_area

        if "confidence" not in hints:
            if "confidence_score" in hints:
                hints["confidence"] = hints.pop("confidence_score")
            elif "confidenceLevel" in hints:
                hints["confidence"] = hints.pop("confidenceLevel")
            else:
                hints["confidence"] = 50

        if isinstance(hints.get("confidence"), str):
            score_str = hints["confidence"].strip().lower()
            if score_str == "low":
                hints["confidence"] = 40
            elif score_str == "medium":
                hints["confidence"] = 70
            elif score_str == "high":
                hints["confidence"] = 90
            else:
                try:
                    hints["confidence"] = int(score_str)
                except ValueError:
                    hints["confidence"] = 50
        elif "confidence" not in hints:
            hints["confidence"] = 50

        if "likely_directories" not in hints or hints["likely_directories"] is None:
            hints["likely_directories"] = []
        elif isinstance(hints["likely_directories"], str):
            hints["likely_directories"] = [hints["likely_directories"]]
            
        if "possible_files" not in hints or hints["possible_files"] is None:
            hints["possible_files"] = []
        elif isinstance(hints["possible_files"], str):
            hints["possible_files"] = [hints["possible_files"]]

        if "reasoning" not in hints:
            hints["reasoning"] = "No reasoning provided."

        return data

    def generate_guidance(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        """Analyze issue and generate exploration hints in a single LLM request."""
        logger.info("Starting issue guidance generation with payload: %s", payload)

        try:
            start_total = time.perf_counter()
            
            validated_payload = IssueGuidanceInput.model_validate(payload)
            issue = validated_payload.issue
            repo_summary = validated_payload.repo_summary
            repository_map = validated_payload.repository_map
            comments = validated_payload.comments
            all_files = validated_payload.all_files
            all_dirs = validated_payload.all_dirs

            # 1. Cache Read Attempt
            owner = issue.get("owner")
            repo = issue.get("repo")
            issue_number = issue.get("number")

            key = None
            cached_guidance = None
            if owner and repo and issue_number:
                try:
                    key = get_issue_guidance_key(owner, repo, issue_number)
                    cached_guidance = self.cache_manager.get(key)
                except Exception as exc:
                    if isinstance(exc, (TypeError, ValueError)):
                        raise
                    logger.warning("[CACHE] Cache check failed for key %s: %s", key or "unknown", exc)

                if cached_guidance is not None:
                    print(f"[CACHE][Issue Guidance #{issue_number}] HIT")
                    return cached_guidance
                else:
                    print(f"[CACHE][Issue Guidance #{issue_number}] MISS")

            metadata = repo_summary.get("metadata", {})
            repo_name = metadata.get("name", "Unknown Repo")
            repo_desc = metadata.get("description", "No description")
            
            # Fetch README and CONTRIBUTING from cache to support prompt builder
            try:
                from app.services.github_service import GitHubService
                gh = GitHubService()
                readme_raw = gh.get_readme(owner, repo) or ""
                contributing_raw = gh.get_contributing(owner, repo) or ""
            except Exception:
                readme_raw = ""
                contributing_raw = ""

            # Prepare base prompt inputs
            repo_purpose = repo_summary.get("summary", {}).get("repository_purpose", "No core purpose")
            repo_beg_summary = repo_summary.get("summary", {}).get("beginner_friendly_summary", "No beginner summary")
            repo_summary_text = f"Repository Purpose: {repo_purpose}\nBeginner Summary: {repo_beg_summary}\n"
            
            instructions_text = COMPRESSED_GUIDANCE_PROMPT_INSTRUCTIONS
            json_schema_text = COMPRESSED_GUIDANCE_PROMPT_SCHEMA
            
            issue_title = issue.get("title", "")
            # Smart issue body truncation (preserve title and body as priority 1)
            issue_body = issue.get("body", "")
            if len(issue_body) > 1500:
                issue_body = issue_body[:1500] + "\n[Body truncated for length]"
            
            issue_labels = issue.get("labels", [])
            issue_labels_str = ", ".join(issue_labels)
            issue_meta_text = f"Issue Title: {issue_title}\nLabels: {issue_labels_str}\n"
            issue_body_text = f"Issue Body (Truncated):\n{issue_body}\n"

            # Remove empty map categories to save tokens
            compact_map = {k: v for k, v in repository_map.items() if v}
            repo_map_raw = json.dumps(compact_map, ensure_ascii=False)

            # Limit candidate files sent
            candidate_files = get_candidate_files(all_files, repository_map)
            scored_candidates = []
            for f in candidate_files:
                score, reasons = score_file(f, issue_title, "", issue_labels)
                scored_candidates.append((score, f, reasons))
            scored_candidates.sort(key=lambda x: (-x[0], x[1]))
            top_candidates = [x[1] for x in scored_candidates[:25]]
            candidate_dirs = sorted(list(set(os.path.dirname(f) for f in top_candidates if os.path.dirname(f))))
            
            map_details = f"Candidate Directories:\n{json.dumps(candidate_dirs, ensure_ascii=False)}\nCandidate Files:\n{json.dumps(top_candidates, ensure_ascii=False)}\n"

            # Adaptive prompt builder loop
            MAX_PROMPT_TOKENS = 1500
            attempt = 0
            success = False
            response = None
            
            while attempt < 4 and not success:
                attempt += 1
                
                # Determine sections inclusion based on attempt configuration
                if attempt == 1:
                    include_map = True
                    include_comments = True
                    compress_readme = False
                    compress_contributing = False
                    include_readme = True
                    include_contributing = True
                elif attempt == 2:
                    include_map = True
                    include_comments = False
                    compress_readme = False
                    compress_contributing = False
                    include_readme = True
                    include_contributing = True
                elif attempt == 3:
                    include_map = True
                    include_comments = False
                    compress_readme = True
                    compress_contributing = True
                    include_readme = True
                    include_contributing = True
                else: # Attempt 4 (Minimal)
                    include_map = False
                    include_comments = False
                    compress_readme = False
                    compress_contributing = False
                    include_readme = False
                    include_contributing = False

                # Format optional sections
                map_text = f"Repository Map:\n{map_details}\n" if include_map else ""
                comments_text = f"Comments:\n{compress_comments(comments)}\n" if (include_comments and comments) else ""
                
                if include_readme:
                    if compress_readme:
                        readme_excerpt = compress_markdown(
                            readme_raw,
                            keep_keywords=["setup", "install", "getting started", "quick start", "contrib", "build", "run"],
                            remove_keywords=["example", "demo", "tutorial", "license", "changelog", "history", "roadmap", "status", "badge", "sponsors", "sponsorship"]
                        )
                    else:
                        readme_excerpt = readme_raw[:2500]
                    readme_text = f"Relevant README Context:\n{readme_excerpt}\n" if readme_excerpt else ""
                else:
                    readme_text = ""
                    
                if include_contributing:
                    if compress_contributing:
                        contributing_excerpt = compress_markdown(
                            contributing_raw,
                            keep_keywords=["workflow", "pull request", "pr", "test", "lint", "style", "standard", "guide"],
                            remove_keywords=["history", "notes", "example", "tutorial", "sponsorship", "thanks"]
                        )
                    else:
                        contributing_excerpt = contributing_raw[:1500]
                    contributing_text = f"Relevant CONTRIBUTING Context:\n{contributing_excerpt}\n" if contributing_excerpt else ""
                else:
                    contributing_text = ""

                # Assemble prompt
                prompt = COMPRESSED_GUIDANCE_PROMPT_TEMPLATE.format(
                    repo_name=repo_name,
                    repo_desc=repo_desc,
                    repo_summary=repo_summary_text,
                    repository_map=map_text,
                    readme=readme_text,
                    contributing=contributing_text,
                    title=issue_title,
                    labels=issue_labels_str,
                    body=issue_body_text,
                    comments=comments_text,
                    instructions=instructions_text,
                    json_schema=json_schema_text
                )
                
                # Observability & Section token calculations
                t_repo_meta = estimate_tokens(f"Repository Context: {repo_name} - {repo_desc}\n{repo_summary_text}")
                t_readme = estimate_tokens(readme_text)
                t_contributing = estimate_tokens(contributing_text)
                t_repo_map = estimate_tokens(map_text)
                t_issue_meta = estimate_tokens(issue_meta_text)
                t_issue_body = estimate_tokens(issue_body_text)
                t_comments = estimate_tokens(comments_text)
                t_instructions = estimate_tokens(instructions_text)
                t_schema = estimate_tokens(json_schema_text)
                
                prompt_tokens = estimate_tokens(prompt)
                
                print(f"\n--------------------------------------------------")
                print(f"Attempt {attempt}")
                print(f"--------------------------------------------------")
                print(f"Prompt Tokens: {prompt_tokens}")
                print(f"Budget: {MAX_PROMPT_TOKENS}")
                print("\nIncluded:")
                print(f"{'[Y]' if include_readme else '[N]'} README" + (" (Compressed)" if (include_readme and compress_readme) else ""))
                print(f"{'[Y]' if include_contributing else '[N]'} CONTRIBUTING" + (" (Compressed)" if (include_contributing and compress_contributing) else ""))
                print(f"{'[Y]' if include_comments else '[N]'} COMMENTS")
                print(f"{'[Y]' if include_map else '[N]'} REPOSITORY MAP")
                
                print(f"\n--------------------------------------------------")
                print(f"Prompt Composition")
                print(f"--------------------------------------------------")
                print(f"Repository Metadata : {t_repo_meta}")
                print(f"README              : {t_readme}")
                print(f"CONTRIBUTING        : {t_contributing}")
                print(f"Repository Map      : {t_repo_map}")
                print(f"Issue Metadata      : {t_issue_meta}")
                print(f"Issue Body          : {t_issue_body}")
                print(f"Comments            : {t_comments}")
                print(f"Instructions        : {t_instructions}")
                print(f"JSON Schema         : {t_schema}")
                print(f"\nTOTAL              : {prompt_tokens}")
                print(f"--------------------------------------------------\n")
                
                if prompt_tokens > MAX_PROMPT_TOKENS:
                    print(f"[BUDGET EXCEEDED] Prompt size {prompt_tokens} exceeds budget {MAX_PROMPT_TOKENS}. Degrading to next attempt level.")
                    continue
                    
                print("Prompt fits within budget. Sending to LLM...")
                try:
                    response = self.llm_service.generate_json(prompt, service_name="Issue Guidance")
                    success = True
                    print("Guidance Generated Successfully")
                    break
                except Exception as e:
                    print(f"LLM Call failed on Attempt {attempt}: {e}")
                    logger.warning("LLM Call failed on Attempt %d: %s", attempt, e)

            # Fallback Guidance Generation if all retries failed
            if not success:
                print("All attempts failed or exceeded budget. Using Graceful Fallback.")
                difficulty = "Beginner"
                labels_lower = [l.lower() for l in issue_labels]
                if "advanced" in labels_lower or "hard" in labels_lower:
                    difficulty = "Advanced"
                elif "intermediate" in labels_lower or "medium" in labels_lower:
                    difficulty = "Intermediate"
                    
                skills = []
                lang = metadata.get("language")
                if lang:
                    skills.append(lang)
                for l in labels_lower:
                    if "python" in l:
                        skills.append("Python")
                    elif "react" in l:
                        skills.append("React")
                    elif "typescript" in l:
                        skills.append("TypeScript")
                    elif "javascript" in l:
                        skills.append("JavaScript")
                    elif "css" in l:
                        skills.append("CSS")
                if not skills:
                    skills = ["General Codebase Concepts"]
                else:
                    skills = list(set(skills))
                    
                affected_area = "General Codebase"
                for l in labels_lower:
                    if "bug" in l:
                        affected_area = "Bug Fix / Troubleshooting"
                    elif "feature" in l:
                        affected_area = "Feature Request / Enhancement"
                    elif "docs" in l or "documentation" in l:
                        affected_area = "Documentation"
                        
                beginner_explanation = (
                    f"This issue relates to the title: '{issue_title}'. "
                    f"It is classified as a '{difficulty}' difficulty task and targets the '{affected_area}' module. "
                    "You can resolve it by setting up the local environment and investigating the suggested paths."
                )
                
                fallback_possible_files = top_candidates[:3] if top_candidates else ["README.md"]
                fallback_likely_dirs = candidate_dirs[:2] if candidate_dirs else ["."]
                reasoning = (
                    f"These codebase locations were identified based on keyword matching with the issue title "
                    f"and labels: {', '.join(issue_labels) if issue_labels else 'None'}."
                )
                
                fallback_data = {
                    "analysis": {
                        "difficulty": difficulty,
                        "skills_required": skills,
                        "affected_area": affected_area,
                        "beginner_explanation": beginner_explanation,
                        "confidence_score": 50
                    },
                    "exploration_hints": {
                        "affected_area": affected_area,
                        "likely_directories": fallback_likely_dirs,
                        "possible_files": fallback_possible_files,
                        "reasoning": reasoning,
                        "confidence": 50
                    }
                }
                
                # Conforms to schemas
                val_guidance = IssueGuidanceOutput.model_validate(fallback_data)
                result_guidance = val_guidance.model_dump()
                result_guidance["guidance_source"] = "fallback"
                print("Fallback Guidance Used")
                return result_guidance

            # Process successful LLM response
            val_start = time.perf_counter()
            response = self.normalize_guidance_response(response, fallback_affected_area="Unknown Area")
            
            # Post-filtering to prevent hallucinations
            full_dirs_set = set(all_dirs)
            full_files_set = set(all_files)
            if full_dirs_set or full_files_set:
                exploration_hints = response.get("exploration_hints", {})
                if isinstance(exploration_hints, dict):
                    exploration_hints["likely_directories"] = [
                        d for d in exploration_hints.get("likely_directories", []) if d in full_dirs_set
                    ]
                    exploration_hints["possible_files"] = [
                        f for f in exploration_hints.get("possible_files", []) if f in full_files_set
                    ]

            guidance = IssueGuidanceOutput.model_validate(response)
            val_dur = time.perf_counter() - val_start
            logger.info("[PERF] Issue Guidance Validation Time: %.2fs", val_dur)

            total_dur = time.perf_counter() - start_total
            logger.info("[PERF] Issue Guidance Total Time: %.2fs", total_dur)

            # Record profiling metrics
            if hasattr(self, "metrics") and isinstance(self.metrics, dict):
                if "guidance_runs" not in self.metrics:
                    self.metrics["guidance_runs"] = []
                self.metrics["guidance_runs"].append({
                    "prompt_tokens": prompt_tokens,
                    "guidance_time": total_dur,
                    "response_tokens": estimate_tokens(json.dumps(response)) if response else 0,
                    "issue_number": issue_number
                })

            result_guidance = guidance.model_dump()
            result_guidance["guidance_source"] = "llm"

            # Cache Write Attempt
            if key and issue_number:
                try:
                    self.cache_manager.set(key, result_guidance, CACHE_TTL_ISSUE_GUIDANCE)
                    print(f"[CACHE WRITE][Issue Guidance #{issue_number}]")
                except Exception as exc:
                    if isinstance(exc, (TypeError, ValueError)):
                        raise
                    logger.warning("[CACHE] Cache write failed for key %s: %s", key, exc)

            logger.info("Issue guidance generation completed successfully")
            return result_guidance

        except Exception as exc:
            logger.exception("Issue guidance generation failed (Validation/Execution): %s", exc)
            raise RuntimeError(f"Failed to generate issue guidance: {exc}") from exc

