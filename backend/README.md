# RepoGuideAI Backend

RepoGuideAI analyzes GitHub repositories and automatically generates beginner-friendly contributor roadmaps, structural maps, and issue exploration hints using LLMs.

## Problem Statement
Open-source onboarding is broken. New contributors spend hours reading scattered documentation and navigating massive codebases just to submit a single "good first issue". RepoGuideAI bridges this gap by automatically parsing the repository and generating intelligent, context-aware instructions for beginners.

## Features
- **Repository Mapping**: Deterministically categorizes directories (Frontend, Backend, Config, etc.) to orient new developers.
- **Issue Contextualization**: Simplifies dense GitHub issues into beginner-friendly summaries with estimated difficulty and required skills.
- **Exploration Hints**: Recommends exactly which files and directories to look at for a given issue.
- **Token Budgeting & Graceful Degradation**: Architected to run under strict LLM API limits (e.g., Groq's 6k TPM) without crashing on partial failures.

## Architecture
* **Framework**: FastAPI + Pydantic
* **LLM Provider**: Groq (Llama 3)
* **GitHub API**: PyGithub

## Setup Instructions

1. Clone the repository and navigate to the backend folder:
   ```bash
   cd backend
   ```
2. Create a virtual environment and install dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```
3. Create your `.env` file based on the example:
   ```bash
   cp .env.example .env
   ```
4. Add your API keys to `.env`:
   - `GROQ_API_KEY`: Get a free key from Groq
   - `GITHUB_TOKEN`: Create a GitHub Personal Access Token

## Running the Backend

Start the development server:
```bash
uvicorn main:app --reload --port 8000
```

## API Documentation
Once the server is running, interactive Swagger documentation is available at:
👉 **http://localhost:8000/docs**

## Testing
A full `FAST_MVP` pipeline analysis can be triggered via a POST request to `/full-analysis` in the Swagger UI.