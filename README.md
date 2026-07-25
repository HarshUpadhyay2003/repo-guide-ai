<div align="center">

<h1>
  <img src="frontend/my-app/public/logos/repo_pilot_icon_no_background.svg" alt="RepoPilot Logo" width="40" align="center" />
  RepoPilot
</h1>

#### AI-Powered Open Source Contribution Assistant

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-0.115+-009688?logo=fastapi&logoColor=white)
![Next.js](https://img.shields.io/badge/Next.js-16.2+-000000?logo=nextdotjs&logoColor=white)
![TypeScript](https://img.shields.io/badge/TypeScript-5.0+-3178C6?logo=typescript&logoColor=white)
![Status](https://img.shields.io/badge/Status-Beta-success)
![Version](https://img.shields.io/badge/Version-v1.0.0--beta-blue)

Helping developers understand repositories, evaluate beginner-friendly issues, and discover where to start contributing.

Instead of spending hours reading documentation, exploring thousands of files, and trying to understand cryptic issue descriptions, RepoPilot provides structured repository insights, issue explanations, exploration guidance, interactive roadmaps, and downloadable PDF reports.

</div>

---

## Current Status

✅ **v1.0.0-beta Released** (Full-Stack Beta Release)

✅ **FastAPI Asynchronous Backend Operational**

✅ **Next.js 16 (React 19) Interactive Dashboard Operational**

✅ **Validated against Major Codebases**: PostHog, LangChain, Supabase, Appwrite

---

## The Problem

Most open-source contribution journeys stall at the onboarding phase:

```text
Find Repository
      ↓
Find Good First Issue
      ↓
Don't Understand Repository Architecture
      ↓
Don't Understand Issue Scope
      ↓
Leave Repository
```

The primary hurdle is rarely coding — it is answering:
* What does this repository do, and what is its underlying tech stack?
* What does this issue actually mean in plain language?
* Can I solve it with my current skillset?
* Which specific files and directories should I read first?

RepoPilot was built to answer those exact questions.

---

## Key Features

### 1. Repository Summary
Generates concise overviews including repo purpose, tech stack, difficulty rating, core concepts, and recommended learning pathways.

### 2. Deterministic Repository Map
Automatically categorizes codebase structure into clean domain areas: Frontend, Backend, Configuration, Documentation, Testing, and Other.

### 3. Good First Issue Discovery
Discovers beginner-friendly issues directly using the GitHub Search API.

### 4. Issue Intelligence & Analysis
Converts complex GitHub issues into beginner-friendly explanations with difficulty estimations, required technical skills, affected system components, and confidence scores.

### 5. Exploration Hints
Provides actionable recommendations for likely directories and specific files to inspect first, complete with clear AI reasoning.

### 6. Contributor Roadmap
Generates structured step-by-step milestones to guide contributors from zero context to submitting their first Pull Request.

### 7. Full PDF Report Export
Generates downloadable, publication-quality PDF executive summaries and issue reports directly from the backend pipeline.

### 8. Built-in Telemetry & Feedback System
Tracks anonymous user analytics and collects structured user feedback via Google Sheets webhooks to continuously improve guidance accuracy.

---

## Architecture

```text
               +----------------------------------+
               |     Next.js 16 (React 19) UI    |
               | Dashboard / Report / PDF / Modal |
               +----------------------------------+
                                |
                        HTTP / REST API
                                |
               +----------------------------------+
               |      FastAPI Backend Engine      |
               | (Middleware, Singleflight, Cache)|
               +----------------------------------+
                     /          |          \
                    /           |           \
      +----------------+ +--------------+ +---------------+
      | GitHub Service | | Groq Service | | PDF Service   |
      | (REST API v3)  | | (Llama-3.3)  | | (ReportLab)   |
      +----------------+ +--------------+ +---------------+
```

---

## Technology Stack

- **Backend**: Python 3.10+, FastAPI, Pydantic v2, PyGithub, Groq API (Llama-3.3-70b-versatile), ReportLab, SQLite / Redis (caching).
- **Frontend**: Next.js 16 (App Router), React 19, TypeScript, TailwindCSS v4, shadcn/ui, Lucide React, Axios.
- **Infrastructure**: Docker, Docker Compose, Uvicorn, Vercel / Render ready.

---

## Folder Structure

```text
repo-guide-ai/
├── backend/                  # FastAPI Python backend
│   ├── app/                  # Application core, API routes, services, schemas
│   ├── evaluation/           # Model benchmarking & agnosticism evaluation scripts
│   ├── scripts/              # Endpoint verification scripts
│   ├── tests/                # Unit and integration tests (pytest)
│   ├── Dockerfile            # Container configuration for backend
│   └── requirements.txt      # Python dependencies
├── docs/                     # Documentation assets and sample analysis JSON
│   ├── backend_testing_swagger.png
│   ├── full_analysis_swagger.png
│   └── sample_posthog_analysis.json
├── frontend/
│   └── my-app/               # Next.js 16 frontend workspace
│       ├── src/              # Components, hooks, services, types, pages
│       ├── public/           # Static assets and branding logos
│       ├── Dockerfile        # Container configuration for frontend
│       └── package.json      # Node.js dependencies & scripts
├── docker-compose.yaml       # Multi-container orchestration specification
├── .env.example              # Full-stack environment template
├── CHANGELOG.md              # Version release history
├── CONTRIBUTING.md           # Guidelines for contributing
├── LICENSE                   # MIT License
└── README.md                 # Project README
```

---

## Quick Start & Installation

### Prerequisites
- Python 3.10+
- Node.js 20+
- Git

### 1. Clone the Repository
```bash
git clone https://github.com/HarshUpadhyay2003/repo-guide-ai.git
cd repo-guide-ai
```

### 2. Backend Setup
```bash
cd backend
python -m venv venv
# On Linux/macOS:
source venv/bin/activate
# On Windows:
venv\Scripts\activate

pip install -r requirements.txt
cp .env.example .env
```
Edit `backend/.env` and add your credentials:
```env
GITHUB_TOKEN=your_github_pat_here
GROQ_API_KEY=your_groq_api_key_here
MODEL_NAME=llama-3.3-70b-versatile
```

Start the FastAPI Backend:
```bash
uvicorn main:app --reload --port 8000
```
Swagger Documentation is available at `http://localhost:8000/docs`.

### 3. Frontend Setup
In a new terminal window:
```bash
cd frontend/my-app
npm install
cp .env.example .env.local
```
Start the Next.js Dev Server:
```bash
npm run dev
```
Open your browser at `http://localhost:3000`.

---

## Running with Docker Compose

Run the entire full-stack application using Docker:

```bash
# Set environment variables or ensure root .env exists
docker-compose up --build
```
Access Frontend at `http://localhost:3000` and Backend API at `http://localhost:8000`.

---

## Environment Variables

### Backend (`backend/.env`)
| Variable | Required | Description |
| :--- | :---: | :--- |
| `GITHUB_TOKEN` | Yes | GitHub Personal Access Token for API requests |
| `GROQ_API_KEY` | Yes | Groq API Key for LLM inference |
| `MODEL_NAME` | Yes | LLM model identifier (default: `llama-3.3-70b-versatile`) |
| `DATABASE_URL` | No | Database connection string |
| `ALLOWED_ORIGINS` | No | Comma-separated CORS allowed origins (`http://localhost:3000,https://repo-guide-ai.vercel.app`) |
| `CACHE_BACKEND` | No | Cache driver (`memory` or `redis`) |

### Frontend (`frontend/my-app/.env.local`)
| Variable | Required | Description |
| :--- | :---: | :--- |
| `NEXT_PUBLIC_API_BASE_URL` | Yes | Base URL for FastAPI Backend (`http://localhost:8000` or production `https://repo-pilot-backend-math.onrender.com`) |
| `NEXT_PUBLIC_REPOPILOT_VERSION` | Yes | App version identifier (`v1.0.0-beta`) |
| `NEXT_PUBLIC_GOOGLE_FORM_URL` | No | Feedback form URL |
| `NEXT_PUBLIC_GOOGLE_SHEETS_WEBHOOK_URL` | No | Feedback submission webhook endpoint |

---

## Production Deployment

- **Frontend Deployment (Vercel)**: `https://repo-guide-ai.vercel.app`
  - Environment Variable: Set `NEXT_PUBLIC_API_BASE_URL=https://repo-pilot-backend-math.onrender.com` in Vercel project settings.
- **Backend Deployment (Render)**: `https://repo-pilot-backend-math.onrender.com`
  - Environment Variable: Set `ALLOWED_ORIGINS=https://repo-guide-ai.vercel.app,http://localhost:3000` in Render service environment settings.

---

## Example Analysis Output

Sample analysis output for PostHog repository:
📄 [View Full Analysis JSON](docs/sample_posthog_analysis.json)

---

## Telemetry & Feedback System

RepoPilot includes opt-in feedback and anonymous client-side telemetry:
- **Telemetry**: Tracks search queries, issue selections, and PDF downloads (privacy-focused, no personal code stored).
- **Feedback System**: Interactive UI feedback modal allows users to submit ratings and suggestions directly to an automated Google Sheets webhook.

---

## Known Limitations

- **Rate Limits**: GitHub REST API allows 5,000 requests/hour with authenticated PATs.
- **Context Size**: Large repositories (>10,000 files) use deterministic directory sampling for map generation.

---

## Roadmap

- [x] **v0.1.0**: Core FastAPI Pipeline & LLM Services
- [x] **v1.0.0-beta**: Next.js Dashboard, Contributor Roadmap, PDF Exports, Telemetry & Feedback
- [ ] **v1.1.0**: Codebase Vector Embeddings & Semantic Search
- [ ] **v1.2.0**: PR Preparation Checklist & Automated Draft Review

---

## Contributing

We welcome contributions! Please review [CONTRIBUTING.md](CONTRIBUTING.md) for local environment setup and pull request workflows.

---

## License

Distributed under the [MIT License](LICENSE).
