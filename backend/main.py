from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_repo import router as repo_router

app = FastAPI(title="Repo Guide AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repo_router)


@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "healthy"}
