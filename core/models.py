from sqlalchemy import Column, String, Text, BIGINT, TIMESTAMP, ForeignKey, Index
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.sql import func
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

    # Relationship to metrics snapshots
    metrics_snapshots = relationship("VideoMetricsSnapshot", back_populates="video")

class VideoMetricsSnapshot(Base):
    """Video metrics snapshot table for time-series analysis"""
    __tablename__ = "video_metrics_snapshot"

    id = Column(BIGINT, primary_key=True, autoincrement=True)
    video_id = Column(String, ForeignKey("videos.video_id"), nullable=False,
                     comment="Reference to video")
    captured_at = Column(TIMESTAMP(timezone=True), nullable=False,
                        default=func.now(), comment="Snapshot capture time (UTC)")
    view_count = Column(BIGINT, comment="View count at capture time")
    like_count = Column(BIGINT, comment="Like count at capture time")
    comment_count = Column(BIGINT, comment="Comment count at capture time")

    # Relationship to video
    video = relationship("Video", back_populates="metrics_snapshots")

    # Index for efficient time-series queries
    __table_args__ = (
        Index('idx_video_metrics_video_captured', 'video_id', 'captured_at'),
    )