# Contributing to RepoPilot

First off, thank you for considering contributing to RepoPilot! It's developers like you that make RepoPilot such a powerful tool for the open-source community.

RepoPilot helps developers understand unfamiliar GitHub repositories, evaluate beginner-friendly issues, and discover where to start contributing.

## Code of Conduct

This project and everyone participating in it is governed by the RepoPilot Code of Conduct. By participating, you are expected to uphold this code.

## Getting Started

RepoPilot consists of a Python FastAPI backend and a Next.js 16 (React 19) frontend.

### Local Development Setup

#### 1. Fork and Clone the Repository
```bash
git clone https://github.com/HarshUpadhyay2003/repo-guide-ai.git
cd repo-guide-ai
```

#### 2. Set up the Backend
```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
cp .env.example .env
```
Add your credentials in `backend/.env`:
- `GITHUB_TOKEN`: A GitHub Personal Access Token
- `GROQ_API_KEY`: A Groq API Key
- `MODEL_NAME`: Default is `llama-3.3-70b-versatile`

Run the backend server:
```bash
uvicorn main:app --reload --port 8000
```
Interactive Swagger documentation will be available at `http://localhost:8000/docs`.

#### 3. Set up the Frontend
In a separate terminal window:
```bash
cd frontend/my-app
npm install
cp .env.example .env.local
```
Run the development server:
```bash
npm run dev
```
Open `http://localhost:3000` in your browser.

## Running Tests

### Backend Tests
Run pytest from the `backend/` directory:
```bash
cd backend
pytest tests
```

### Frontend Typecheck & Build
Run build verification from `frontend/my-app/`:
```bash
cd frontend/my-app
npm run build
```

## Development Workflow & Pull Requests

1. Create a new branch for your feature or bugfix (`git checkout -b feature/amazing-feature`).
2. Write clear, structured code matching existing application patterns.
3. Verify backend tests pass (`pytest tests`) and frontend builds without errors (`npm run build`).
4. Commit your changes with descriptive messages (`git commit -m 'Add support for custom model endpoints'`).
5. Push to your branch (`git push origin feature/amazing-feature`).
6. Open a Pull Request against the `main` branch.

## Issue Reporting Guidelines

If you find a bug or have a feature request, please open an issue! When reporting, include:
- A descriptive title.
- Steps to reproduce the bug.
- Expected behavior vs. actual behavior.
- Information about your local environment (OS, Python version, Node version).