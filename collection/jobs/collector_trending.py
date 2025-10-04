#!/usr/bin/env python3
import sys
import logging
import argparse
from datetime import datetime, timezone
from typing import List

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, ".")

from core.db import SessionLocal
from core.models import Video, VideoMetricsSnapshot
from core.logging import setup_json_logging
from collection.clients.youtube import YouTubeClient, YouTubeVideo

logger = logging.getLogger(__name__)

class TrendingCollector:
    def __init__(self):
        self.db = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def collect_trending(self, country_code: str = "KR", limit: int = 50):
        """Collect trending videos and store in database"""
        trace_id = f"collect_trending_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        try:
            logger.info(f"Starting trending collection", extra={
                "trace_id": trace_id,
                "country_code": country_code,
                "limit": limit
            })

            # Fetch trending videos from YouTube
            with YouTubeClient() as youtube:
                videos = youtube.get_trending_videos(country_code, limit)

            if not videos:
                logger.warning("No videos fetched", extra={"trace_id": trace_id})
                return

            # Store videos and metrics
            videos_stored = self._upsert_videos(videos, trace_id)
            snapshots_stored = self._insert_metrics_snapshots(videos, trace_id)

            logger.info(f"Collection completed", extra={
                "trace_id": trace_id,
                "videos_stored": videos_stored,
                "snapshots_stored": snapshots_stored
            })

        except Exception as e:
            logger.error(f"Collection failed: {e}", extra={"trace_id": trace_id})
            raise

    def _upsert_videos(self, videos: List[YouTubeVideo], trace_id: str) -> int:
        """Upsert videos into videos table"""
        try:
            video_data = []
            for video in videos:
                video_data.append({
                    "video_id": video.video_id,
                    "title": video.title,
                    "description": video.description,
                    "channel": video.channel,
                    "category": video.category,
                    "tags": video.tags,
                    "country_code": video.country_code,
                    "published_at": video.published_at
                })

            stmt = insert(Video).values(video_data)
            stmt = stmt.on_conflict_do_update(
                index_elements=["video_id"],
                set_={
                    "title": stmt.excluded.title,
                    "description": stmt.excluded.description,
                    "channel": stmt.excluded.channel,
                    "category": stmt.excluded.category,
                    "tags": stmt.excluded.tags,
                    "country_code": stmt.excluded.country_code,
                    "published_at": stmt.excluded.published_at
                }
            )

            result = self.db.execute(stmt)
            self.db.commit()

            return len(video_data)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upsert videos: {e}", extra={"trace_id": trace_id})
            raise

    def _insert_metrics_snapshots(self, videos: List[YouTubeVideo], trace_id: str) -> int:
        """Insert metrics snapshots"""
        try:
            captured_at = datetime.now(timezone.utc)
            snapshot_data = []

            for video in videos:
                snapshot_data.append({
                    "video_id": video.video_id,
                    "captured_at": captured_at,
                    "view_count": video.view_count,
                    "like_count": video.like_count,
                    "comment_count": video.comment_count
                })

            self.db.bulk_insert_mappings(VideoMetricsSnapshot, snapshot_data)
            self.db.commit()

            return len(snapshot_data)

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to insert metrics snapshots: {e}", extra={"trace_id": trace_id})
            raise

def main():
    parser = argparse.ArgumentParser(description="Collect trending videos from YouTube")
    parser.add_argument("--country", default="KR", help="Country code (default: KR)")
    parser.add_argument("--limit", type=int, default=50, help="Max videos to collect (default: 50)")

    args = parser.parse_args()

    setup_json_logging()

    with TrendingCollector() as collector:
        collector.collect_trending(args.country, args.limit)

if __name__ == "__main__":
    main()