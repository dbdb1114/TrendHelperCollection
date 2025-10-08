"""Health service for basic health checks"""
import logging
from datetime import datetime, timezone
from typing import Dict, Any

from service.dto import HealthResponseDTO

logger = logging.getLogger(__name__)


def get_health() -> HealthResponseDTO:
    """
    Get basic health status.

    v1: Returns static OK status
    v2: Will include DB ping, dependency checks

    Returns:
        HealthResponseDTO: Health check result
    """
    logger.info("Health check requested")

    return HealthResponseDTO(
        ok=True,
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0"
    )