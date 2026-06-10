import inspect
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.routes_repo import router as repo_router
from app.services.repository_map_service import RepositoryMapService

logger = logging.getLogger(__name__)

app = FastAPI(title="Repo Guide AI", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(repo_router)

@app.on_event("startup")
async def startup_event():
    """Validate the RepositoryMapService constructor at startup."""
    sig = inspect.signature(RepositoryMapService.__init__)
    logger.info("RepositoryMapService constructor signature: %s", sig)

@app.get("/health", tags=["health"])
def health_check() -> dict[str, str]:
    """Return the service health status."""
    return {"status": "healthy"}
