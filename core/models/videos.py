from sqlalchemy import Column, String, Text, TIMESTAMP
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from core.db import Base

class Video(Base):
    """Video metadata table"""
    __tablename__ = "videos"

    video_id = Column(String, primary_key=True, comment="YouTube video ID")
    title = Column(Text, comment="Video title")
    description = Column(Text, comment="Video description")
    channel = Column(Text, comment="Channel name")
    category = Column(Text, comment="Category ID")
    tags = Column(JSONB, comment="Video tags as JSON array")
    country_code = Column(Text, comment="Country code (e.g., KR)")
    published_at = Column(TIMESTAMP(timezone=True), comment="Video publication time (UTC)")

    metrics_snapshots = relationship("VideoMetricsSnapshot", back_populates="video")