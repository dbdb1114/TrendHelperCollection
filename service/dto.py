"""Data Transfer Objects for service layer"""
from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field


class IdeaRequestDTO(BaseModel):
    """Service layer DTO for idea generation requests"""
    video_id: Optional[str] = None
    keywords: List[str] = Field(default=[], max_items=10)
    signals: Dict[str, Any] = Field(default_factory=dict)
    style: Dict[str, Any] = Field(default_factory=lambda: {
        "tone": "info",
        "language": "ko",
        "length_sec": "20"
    })


class IdeaResponseDTO(BaseModel):
    """Service layer DTO for idea generation responses"""
    titles: List[str] = Field(min_items=3, max_items=5)
    tags: List[str] = Field(min_items=5, max_items=10)
    script_beats: Dict[str, str] = Field(default_factory=dict)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class HealthResponseDTO(BaseModel):
    """Service layer DTO for health check responses"""
    ok: bool = True
    timestamp: Optional[str] = None
    version: Optional[str] = None