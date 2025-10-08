"""Ideas service for content generation orchestration"""
import logging
import time
from typing import Any

from sqlalchemy.orm import Session

from service.dto import IdeaRequestDTO, IdeaResponseDTO
from generation.clients.model_client import IdeaModelClient
from generation.schemas.idea import IdeaRequest, IdeaResponse

logger = logging.getLogger(__name__)


class DomainValidationError(Exception):
    """Domain validation error for service layer"""
    def __init__(self, message: str, code: str = "VALIDATION_FAILED"):
        self.message = message
        self.code = code
        super().__init__(message)


class DependencyError(Exception):
    """Dependency error for external service failures"""
    def __init__(self, message: str, code: str = "DEPENDENCY_UNAVAILABLE"):
        self.message = message
        self.code = code
        super().__init__(message)


def create_ideas(
    dto: IdeaRequestDTO,
    *,
    trace_id: str,
    session: Session,
    model_client: IdeaModelClient
) -> IdeaResponseDTO:
    """
    Generate content ideas based on request DTO.

    Args:
        dto: Validated request DTO
        trace_id: Request tracing ID
        session: Database session (for future video context lookup)
        model_client: Model client for generation

    Returns:
        IdeaResponseDTO: Generated ideas with metadata

    Raises:
        DomainValidationError: Validation/guardrails failure
        DependencyError: External service failure
    """
    start_time = time.time()

    logger.info("Starting idea generation", extra={
        "trace_id": trace_id,
        "video_id": dto.video_id,
        "keywords": dto.keywords,
        "signals": list(dto.signals.keys())
    })

    try:
        # Convert DTO to generation schema
        idea_request = IdeaRequest(
            video_id=dto.video_id,
            keywords=dto.keywords,
            signals=dto.signals,
            style=dto.style
        )

        # Call generation layer
        idea_response: IdeaResponse = model_client.generate_ideas(
            idea_request, trace_id
        )

        # Convert to service DTO
        response_dto = IdeaResponseDTO(
            titles=idea_response.titles,
            tags=idea_response.tags,
            script_beats=idea_response.script_beats.dict(),
            metadata=idea_response.metadata
        )

        latency_ms = int((time.time() - start_time) * 1000)

        logger.info("Idea generation completed", extra={
            "trace_id": trace_id,
            "latency_ms": latency_ms,
            "titles_count": len(response_dto.titles),
            "tags_count": len(response_dto.tags),
            "model": response_dto.metadata.get("model", "unknown")
        })

        return response_dto

    except ValueError as e:
        # Pydantic validation or guardrails failure
        logger.warning("Validation failed during idea generation", extra={
            "trace_id": trace_id,
            "error": str(e)
        })
        raise DomainValidationError(
            f"Validation failed: {str(e)}",
            code="VALIDATION_FAILED"
        )

    except Exception as e:
        # External service or unexpected errors
        logger.error("Idea generation failed", extra={
            "trace_id": trace_id,
            "error": str(e),
            "error_type": type(e).__name__
        })
        raise DependencyError(
            f"Generation service unavailable: {str(e)}",
            code="DEPENDENCY_UNAVAILABLE"
        )