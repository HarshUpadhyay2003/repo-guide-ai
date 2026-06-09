REPOSITORY_MAP_PROMPT = """
You are a software engineering assistant analyzing a repository directory structure.

Use the provided list of directories extracted from the repository to categorize them.
Focus on top-level and important second-level directories.

Repository Directories:
{directories}

Categorize the directories into the following JSON schema:
{{
  "frontend": ["list of frontend related directories"],
  "backend": ["list of backend related directories"],
  "tests": ["list of test related directories"],
  "docs": ["list of documentation related directories"],
  "config": ["list of configuration or CI/CD related directories"],
  "scripts": ["list of scripts or tooling directories"],
  "other": ["list of other important directories that don't fit above"]
}}

Rules:
- Output valid JSON only.
- Do not add any markdown formatting like ```json.
- Include the exact directory paths as strings.
- Keep the arrays empty if no directories fit the category.
"""