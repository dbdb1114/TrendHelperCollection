from sqlalchemy import Column, String, BIGINT, TIMESTAMP, ForeignKey, Index
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from core.db import Base

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

    video = relationship("Video", back_populates="metrics_snapshots")

    __table_args__ = (
        Index('idx_video_metrics_video_captured', 'video_id', 'captured_at'),
    )