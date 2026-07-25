# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0-beta] - 2026-07-24

### Added
- **Next.js 16 Web Dashboard**: Built interactive UI powered by React 19, TypeScript, and TailwindCSS v4.
- **Contributor Roadmap Service**: Added backend service generating actionable step-by-step milestones for issue resolution.
- **PDF Report Generation**: Integrated backend ReportLab PDF generation for full repository analyses and issue guidance reports.
- **Telemetry & Feedback Modal**: Added client-side telemetry tracking and Google Sheets webhook integration for collecting user feedback.
- **Singleflight Concurrency Control**: Deduplicated concurrent identical repository analysis requests in the backend.
- **Docker Compose Containerization**: Added multi-container Docker Compose configuration for backend and frontend.

### Changed
- Refactored repository structure: Moved all backend test files into `backend/tests/`.
- Sanitized environment variables and updated `.env.example` templates across full stack.

---

## [0.1.0] - 2026-07-10

### Added
- **Repository Summary Service**: Automatically generates repository purpose, tech stack, difficulty level, and learning recommendations.
- **Repository Map Service**: Deterministically categorizes repository structure into Frontend, Backend, Config, Docs, Tests, and Other domains.
- **Good First Issue Discovery**: Integration with GitHub Search API to find beginner-friendly open-source issues.
- **Issue Analysis Service**: Generates difficulty estimations, required technical skills, affected system areas, beginner-friendly explanations, and confidence scores.
- **Exploration Hints**: AI-driven suggestions providing likely directories and specific files to explore.
- **FastAPI Application Ecosystem**: Complete REST API with Swagger documentation (`/docs`) and robust error handling.