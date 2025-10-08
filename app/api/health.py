"""Health check API endpoints"""
from fastapi import APIRouter

from service.health_service import get_health
from service.dto import HealthResponseDTO

router = APIRouter(tags=["health"])


@router.get("/health", response_model=HealthResponseDTO)
def health_check() -> HealthResponseDTO:
    """
    Basic health check endpoint.

    Returns:
        HealthResponseDTO: Health status with timestamp
    """
    return get_health()