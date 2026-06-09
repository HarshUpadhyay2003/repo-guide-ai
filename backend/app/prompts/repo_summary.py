REPO_SUMMARY_PROMPT = """
You are helping a beginner understand a GitHub repository.

Use the following inputs:
- README: {readme}
- CONTRIBUTING: {contributing}
- Metadata: {metadata}

Create a concise, beginner-friendly explanation of the repository.
Return valid JSON only with this exact schema:
{{
  "repository_purpose": "",
  "target_users": "",
  "difficulty_level": "",
  "estimated_learning_time": "",
  "tech_stack": [],
  "key_concepts": [],
  "beginner_friendly_summary": "",
  "first_steps": []
}}

Rules:
- Output JSON only. No markdown fences, no commentary, no extra text.
- Keep the explanation beginner-friendly.
- Use plain language and practical examples.
- If information is missing, use empty strings or empty arrays.
"""
