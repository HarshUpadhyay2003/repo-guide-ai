# Project Status

**Project:** RepoGuideAI  
**Tagline:** AI-Powered Open Source Contribution Assistant  
**Current Version:** v0.1.0 (Backend MVP)

## Current State

The project has completed the **Backend MVP (v0.1.0)** phase. We have successfully realized the product evolution from an "AI Repository Summarizer" into a comprehensive "Open Source Contribution Assistant". 

The core data processing pipeline, LLM integrations, and API endpoints are fully operational and have been validated against major open-source repositories (PostHog, LangChain, Supabase, Appwrite).

## Completed Milestone: Backend MVP (v0.1.0)

The following features and infrastructure are completed and deployed via the FastAPI application:

- **Repository Summary**: Generation of repo purpose, tech stack, and difficulty evaluation.
- **Repository Map**: Deterministic directory categorization (Frontend, Backend, Config, Docs, Tests, Other).
- **Good First Issue Discovery**: Automated fetching of beginner-friendly issues via the GitHub Search API.
- **Issue Analysis**: AI-driven generation of difficulty scores, required skills, affected system areas, and beginner explanations.
- **Exploration Hints**: Predictive recommendations for directories and files to investigate, complete with AI reasoning.
- **Infrastructure**: Fully structured JSON outputs via Pydantic, graceful error handling, Swagger testing environment, and multi-repository validation.

## Under Development: Frontend App (v0.2.0)

Development is now shifting to the user interface. The frontend is currently under development using **Next.js, TypeScript, TailwindCSS, and shadcn/ui**. Features currently being built include:

- **Frontend Dashboard**: A centralized UI for developers to search and analyze repositories.
- **Repository Visualization**: Graphical representation of the backend's repository map.
- **Issue Detail UI**: An elegant interface for displaying the generated issue analysis and exploration hints side-by-side with the codebase logic.

## Future Roadmap

Looking beyond v0.2.0, the project will expand to include advanced contextual capabilities:

- **Repository Embeddings & Semantic Search**: Vectorizing the codebase to allow natural language querying and precise, exact file localization.
- **Issue Similarity Search**: Finding past solved issues similar to new ones to learn from previous Pull Requests.
- **PR Guidance & Contribution Checklists**: Generating step-by-step guides to successfully prepare and submit a pull request.