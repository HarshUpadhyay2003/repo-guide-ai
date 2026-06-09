ROADMAP_PROMPT = """
You are helping a beginner create a practical contribution roadmap.

Generate a simple 5-step roadmap for contributing to the repository.
Return valid JSON only with this exact schema:
{{
  "step_1": "",
  "step_2": "",
  "step_3": "",
  "step_4": "",
  "step_5": "",
  "recommended_first_issue_type": "",
  "success_tips": []
}}

Rules:
- Output JSON only. No markdown fences, no commentary, no extra text.
- Keep the roadmap beginner-friendly and actionable.
- If information is missing, use empty strings or empty arrays.
"""
