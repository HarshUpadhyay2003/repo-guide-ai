CONTRIBUTOR_ROADMAP_PROMPT = """
You are helping a beginner choose a first contribution path for a GitHub repository.

Use these inputs:
- Repository summary: {repo_summary}
- Tree analysis: {tree_analysis}
- Candidate issues: {issues}

Choose the best issue to start with, explain why it is a good beginner choice, and recommend a simple learning and contribution order.
Return valid JSON only with this exact schema:
{{
  "best_issue_to_start": {{
    "issue_number": 1,
    "title": "Example issue"
  }},
  "why_this_issue": "Why this issue fits a beginner",
  "recommended_learning_order": ["Read README", "Explore src", "Run tests"],
  "files_to_read_first": ["README.md", "CONTRIBUTING.md", "src/main.py"],
  "contribution_plan": ["Set up the project", "Implement a small fix", "Submit a PR"],
  "success_tips": ["Ask for help early", "Keep changes small"]
}}

Rules:
- Output JSON only.
- Keep the guidance beginner-friendly and practical.
- Pick the most suitable issue from the candidate list when possible.
- If no issue is useful, choose a small documentation or setup task.
"""
