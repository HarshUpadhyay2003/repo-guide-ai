TREE_ANALYSIS_PROMPT = """
You are helping a beginner understand a repository structure.

Use these inputs:
- Repository summary: {repo_summary}
- Top-level folders: {tree}

Analyze only the important top-level folders. Ignore build, cache, and dependency folders.
Return valid JSON only with this exact schema:
{{
  "folders": [
    {{
      "name": "src",
      "purpose": "Main application code",
      "difficulty": "Easy",
      "should_beginner_touch": true,
      "learning_priority": 1
    }}
  ],
  "best_folder_for_beginners": "src",
  "recommended_exploration_order": ["src", "tests", "docs"]
}}

Rules:
- Output JSON only.
- Keep explanations short and beginner-friendly.
- Use only the most relevant folders.
- If there are no useful folders, return an empty folders array.
"""
