ISSUE_ANALYSIS_PROMPT = """
You are helping a beginner contributor understand a GitHub issue.

Use these inputs:
- Issue title: {title}
- Issue body: {body}
- Labels: {labels}
- Repository summary: {repo_summary}

Explain the issue clearly for a beginner. Focus on what the issue is, why it matters, and the first practical step to take.
Return valid JSON only with this exact schema:
{{
  "difficulty": "Beginner",
  "estimated_hours": 2,
  "skills_required": ["Python"],
  "concepts_to_understand": ["Testing"],
  "what_needs_to_be_done": "",
  "beginner_explanation": "",
  "files_likely_affected": ["src/example.py"],
  "recommended_first_step": "",
  "confidence_score": 85
}}

Rules:
- Output JSON only. No markdown fences, no commentary, no extra text.
- Use the exact field names shown above.
- Difficulty must be one of: Beginner, Intermediate, Advanced.
- estimated_hours must be an integer.
- confidence_score must be an integer from 0 to 100.
- If information is missing, use reasonable defaults.
"""
