ISSUE_ANALYSIS_PROMPT = """
You are helping a beginner contributor understand a GitHub issue.

Use these inputs:
- Repository summary: {repo_summary}
- Repository map: {repository_map}
- Issue title: {title}
- Issue body: {body}
- Labels: {labels}
- Issue comments: {comments}

Explain the issue clearly for a beginner. Focus on what the issue is, why it matters, and the first practical step to take.
- Use the repository map to identify the affected area.
- Use maintainer hints from comments to guide your explanation.
- Do not hallucinate technologies not mentioned in the repository summary or map.
- Explain your reasoning so a beginner can understand why these skills and areas are involved.

Return valid JSON only with this exact schema:
{{
  "difficulty": "Beginner",
  "skills_required": ["Python"],
  "affected_area": "src/backend",
  "beginner_explanation": "Detailed explanation of what needs to be done and why...",
  "confidence_score": 85
}}

Rules:
- Output JSON only. No markdown fences, no commentary, no extra text.
- Use the exact field names shown above.
- Difficulty must be one of: Beginner, Intermediate, Advanced.
- confidence_score must be an integer from 0 to 100.
- If information is missing, use reasonable defaults.
"""
