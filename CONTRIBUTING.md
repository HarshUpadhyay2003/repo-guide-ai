# Contributing to RepoGuideAI

First off, thank you for considering contributing to RepoGuideAI! It's developers like you that make RepoGuideAI such a powerful tool for the open-source community. 

RepoGuideAI helps developers understand unfamiliar GitHub repositories, evaluate beginner-friendly issues, and discover where to start contributing. 

## Code of Conduct

This project and everyone participating in it is governed by the RepoGuideAI Code of Conduct. By participating, you are expected to uphold this code.

## Getting Started

The current project architecture consists of a Python FastAPI backend. (The Next.js frontend is planned for v0.2.0).

### Local Development Setup

1. **Fork and Clone the Repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/RepoGuideAI.git
   cd RepoGuideAI/backend
   ```

2. **Set up the Virtual Environment**
   ```bash
   python3 -m venv venv
   source venv/bin/activate  # On Windows use `venv\Scripts\activate`
   ```

3. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Copy the example environment file and add your credentials:
   ```bash
   cp .env.example .env
   ```
   Required keys:
   - `GITHUB_TOKEN`: A GitHub Personal Access Token
   - `GROQ_API_KEY`: A Groq API Key
   - `MODEL_NAME`: Default is `llama-3.3-70b-versatile`

5. **Run the API Server**
   ```bash
   uvicorn main:app --reload
   ```
   Interactive Swagger documentation will be available at `http://localhost:8000/docs`.

## Development Workflow & Pull Requests

1. Create a new branch for your feature or bugfix (`git checkout -b feature/amazing-feature`).
2. Write clear, structured code matching the existing pipeline pattern.
3. Commit your changes with descriptive messages (`git commit -m 'Add new codebase embedding module'`).
4. Push to your branch (`git push origin feature/amazing-feature`).
5. Open a Pull Request against the `main` branch.

## Issue Reporting Guidelines

If you find a bug or have a feature request, please open an issue! When reporting, include:
- A descriptive title.
- Steps to reproduce the bug (if applicable).
- Expected behavior vs. actual behavior.
- Information about your local environment (OS, Python version).