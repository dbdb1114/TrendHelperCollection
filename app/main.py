from fastapi import FastAPI
import logging

from app.api.ideas import router as ideas_router
from app.api.health import router as health_router
from core.logging import setup_json_logging

# Setup logging
setup_json_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Trend Helper API", version="0.1.0")

# Include routers
app.include_router(health_router)  # Health at root level
app.include_router(ideas_router, prefix="/api/v1")
