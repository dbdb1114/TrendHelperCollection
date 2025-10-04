import logging
from datetime import datetime, timezone
from fastapi import APIRouter, HTTPException

from generation.clients.claude import ClaudeClient
from generation.schemas import IdeaRequest, IdeaResponse

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/ideas", response_model=IdeaResponse)
async def generate_ideas(request: IdeaRequest) -> IdeaResponse:
    """Generate content ideas based on trending signals and keywords"""
    trace_id = f"api_ideas_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

    try:
        logger.info("Ideas API request received", extra={
            "trace_id": trace_id,
            "keywords": request.keywords,
            "video_id": request.video_id,
            "signals": request.signals
        })

        # Generate ideas using Claude
        with ClaudeClient() as claude:
            response = claude.generate_ideas(request, trace_id)

        logger.info("Ideas API request completed", extra={
            "trace_id": trace_id,
            "titles_count": len(response.titles),
            "tags_count": len(response.tags),
            "retry_count": response.metadata.get("retry_count", 0)
        })

        return response

    except Exception as e:
        logger.error(f"Ideas API request failed: {e}", extra={
            "trace_id": trace_id,
            "error_type": type(e).__name__
        })

        raise HTTPException(
            status_code=500,
            detail={
                "error": "Content generation failed",
                "trace_id": trace_id,
                "type": type(e).__name__
            }
        )

@router.get("/ideas/health")
async def ideas_health():
    """Health check for ideas service"""
    return {
        "service": "ideas",
        "status": "healthy",
        "timestamp": datetime.now(timezone.utc).isoformat()
    }