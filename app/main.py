from fastapi import FastAPI
import logging

from app.api.ideas import router as ideas_router
from core.logging import setup_json_logging

# Setup logging
setup_json_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Trend Helper API", version="0.1.0")

# Include routers
app.include_router(ideas_router, prefix="/api/v1")

@app.get("/health")
def health():
    return {"ok": True}
