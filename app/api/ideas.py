import logging
from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session

from app.deps.common import get_db_session, get_trace_id, get_model_client
from service.dto import IdeaRequestDTO, IdeaResponseDTO
from service.ideas_service import create_ideas, DomainValidationError, DependencyError
from generation.clients.model_client import IdeaModelClient

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ideas"])


@router.post("/ideas", response_model=IdeaResponseDTO)
def generate_ideas(
    request: IdeaRequestDTO,
    session: Session = Depends(get_db_session),
    trace_id: str = Depends(get_trace_id),
    model_client: IdeaModelClient = Depends(get_model_client)
) -> IdeaResponseDTO:
    """Generate content ideas based on trending signals and keywords"""
    try:
        logger.info("Ideas API request received", extra={
            "trace_id": trace_id,
            "keywords": request.keywords,
            "video_id": request.video_id,
            "signals": list(request.signals.keys())
        })

        # Call service layer
        response = create_ideas(
            request,
            trace_id=trace_id,
            session=session,
            model_client=model_client
        )

        logger.info("Ideas API request completed", extra={
            "trace_id": trace_id,
            "titles_count": len(response.titles),
            "tags_count": len(response.tags)
        })

        return response

    except DomainValidationError as e:
        logger.warning("Domain validation error", extra={
            "trace_id": trace_id,
            "error_code": e.code,
            "error_message": e.message
        })
        raise HTTPException(
            status_code=422,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": trace_id
                }
            }
        )

    except DependencyError as e:
        logger.error("Dependency error", extra={
            "trace_id": trace_id,
            "error_code": e.code,
            "error_message": e.message
        })
        raise HTTPException(
            status_code=503,
            detail={
                "error": {
                    "code": e.code,
                    "message": e.message,
                    "trace_id": trace_id
                }
            }
        )

    except Exception as e:
        logger.error("Unexpected error", extra={
            "trace_id": trace_id,
            "error_type": type(e).__name__,
            "error_message": str(e)
        })
        raise HTTPException(
            status_code=500,
            detail={
                "error": {
                    "code": "INTERNAL_ERROR",
                    "message": "Internal server error",
                    "trace_id": trace_id
                }
            }
        )