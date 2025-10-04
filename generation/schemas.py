from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field, validator
import re

class IdeaRequest(BaseModel):
    video_id: Optional[str] = None
    keywords: List[str] = Field(..., min_items=1, max_items=10)
    signals: Dict[str, float] = Field(default_factory=dict)
    style: Dict[str, str] = Field(default_factory=lambda: {
        "tone": "info",
        "language": "ko",
        "length_sec": "20"
    })

class ScriptBeats(BaseModel):
    hook: str = Field(..., min_length=10, max_length=200)
    body: str = Field(..., min_length=20, max_length=500)
    cta: str = Field(..., min_length=10, max_length=100)

class IdeaResponse(BaseModel):
    titles: List[str] = Field(..., min_items=3, max_items=5)
    tags: List[str] = Field(..., min_items=5, max_items=10)
    script_beats: ScriptBeats
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @validator('titles')
    def validate_titles(cls, v):
        for title in v:
            # Length check (20-35 chars)
            if not 20 <= len(title) <= 35:
                raise ValueError(f"Title length must be 20-35 chars: {title}")

            # Emoji count check (≤ 1)
            emoji_count = len(re.findall(r'[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]', title))
            if emoji_count > 1:
                raise ValueError(f"Too many emojis in title: {title}")

            # Forbidden patterns
            forbidden = ['클릭', '충격', '경악', '실화', '미친', '대박']
            if any(word in title for word in forbidden):
                raise ValueError(f"Forbidden clickbait words in title: {title}")

        return v

    @validator('tags')
    def validate_tags(cls, v):
        for tag in v:
            # Must start with #
            if not tag.startswith('#'):
                raise ValueError(f"Tag must start with #: {tag}")

            # Length check
            if len(tag) > 20:
                raise ValueError(f"Tag too long: {tag}")

            # No PII or forbidden content
            forbidden = ['개인정보', '전화번호', '이메일']
            if any(word in tag for word in forbidden):
                raise ValueError(f"Forbidden content in tag: {tag}")

        return v

class GenerationMetadata(BaseModel):
    model: str
    safety_flags: List[str] = Field(default_factory=list)
    generation_time: float
    retry_count: int = 0