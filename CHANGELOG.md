# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - Initial Backend MVP Release

### Added
- **Repository Summary Service**: Automatically generates repository purpose, tech stack, difficulty level, and learning recommendations.
- **Repository Map Service**: Deterministically categorizes repository structure into Frontend, Backend, Config, Docs, Tests, and Other domains.
- **Good First Issue Discovery**: Integration with GitHub Search API to find beginner-friendly open-source issues.
- **Issue Analysis Service**: Generates difficulty estimations, required technical skills, affected system areas, beginner-friendly explanations, and confidence scores for selected issues.
- **Exploration Hints**: AI-driven suggestions providing likely directories and specific files to explore when tackling an issue, accompanied by reasoning.
- **Structured Data Pipeline**: Complete deterministic JSON output structuring for seamless API consumption.
- **FastAPI Application Ecosystem**: Complete REST API with Swagger documentation (`/docs`) and robust error handling.
- **LLM Integration**: Pipeline utilizing the Groq API for lightning-fast inference.
- **Multi-Repository Validation**: Validated logic and LLM outputs against major codebases including PostHog, LangChain, Supabase, and Appwrite.

### Changed
- Transitioned primary project focus from "AI Repository Summarizer" to "AI Open Source Contribution Assistant".