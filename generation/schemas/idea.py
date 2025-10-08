"""Pydantic schemas for idea generation with guardrails validation"""
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
from generation.guardrails.rules import validate_titles, validate_tags, validate_script_beats

class IdeaRequest(BaseModel):
    """Request schema for idea generation"""
    video_id: Optional[str] = None
    keywords: List[str] = Field(default=[], max_items=10)
    signals: Dict[str, float] = Field(default_factory=dict)
    style: Dict[str, str] = Field(default_factory=lambda: {
        "tone": "info",
        "language": "ko",
        "length_sec": "20"
    })

class ScriptBeats(BaseModel):
    """3-Beat script structure: Hook → Body → CTA"""
    hook: str = Field(..., min_length=10, max_length=200)
    body: str = Field(..., min_length=20, max_length=500)
    cta: str = Field(..., min_length=10, max_length=100)

class IdeaResponse(BaseModel):
    """Response schema for generated ideas with guardrails validation"""
    titles: List[str] = Field(..., min_items=3, max_items=5)
    tags: List[str] = Field(..., min_items=5, max_items=10)
    script_beats: ScriptBeats
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('titles')
    def validate_titles_guardrails(cls, v):
        violations = validate_titles(v)
        if violations:
            raise ValueError(f"Title guardrail violations: {violations}")
        return v

    @validator('tags')
    def validate_tags_guardrails(cls, v):
        violations = validate_tags(v)
        if violations:
            raise ValueError(f"Tag guardrail violations: {violations}")
        return v

    @validator('script_beats')
    def validate_script_guardrails(cls, v):
        violations = validate_script_beats(v.model_dump())
        if violations:
            raise ValueError(f"Script guardrail violations: {violations}")
        return v

class GenerationMetadata(BaseModel):
    """Metadata for generation tracking and safety"""
    model: str
    safety_flags: List[str] = Field(default_factory=list)
    generation_time: float
    retry_count: int = 0