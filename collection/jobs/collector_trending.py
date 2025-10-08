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

    def collect_trending(self, country_code: str = "KR", limit: int = 50, dry_run: bool = False):
        """Collect trending videos and store in database"""
        trace_id = f"collect_trending_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"
        errors = 0

        try:
            logger.info(f"Starting trending collection", extra={
                "trace_id": trace_id,
                "job": "collector_trending",
                "country_code": country_code,
                "limit": limit,
                "dry_run": dry_run
            })

            # Fetch trending videos from YouTube
            with YouTubeClient() as youtube:
                videos = youtube.get_trending_videos(country_code, limit)

            if not videos:
                logger.warning("No videos fetched", extra={"trace_id": trace_id})
                return 0, 0, 0

            logger.info(f"Fetched {len(videos)} videos", extra={
                "trace_id": trace_id,
                "fetched": len(videos)
            })

            if dry_run:
                logger.info("Dry run mode - no database changes", extra={
                    "trace_id": trace_id,
                    "would_upsert": len(videos),
                    "would_snapshot": len(videos)
                })
                return len(videos), len(videos), 0

            # Store videos and metrics
            videos_stored, video_errors = self._upsert_videos(videos, trace_id)
            snapshots_stored, snapshot_errors = self._insert_metrics_snapshots(videos, trace_id)
            errors = video_errors + snapshot_errors

            logger.info(f"Collection completed", extra={
                "trace_id": trace_id,
                "job": "collector_trending",
                "country": country_code,
                "fetched": len(videos),
                "upserts": videos_stored,
                "snapshots": snapshots_stored,
                "errors": errors
            })

            return len(videos), videos_stored, snapshots_stored

        except Exception as e:
            logger.error(f"Collection failed: {e}", extra={
                "trace_id": trace_id,
                "job": "collector_trending",
                "errors": errors + 1
            })
            raise

    def _upsert_videos(self, videos: List[YouTubeVideo], trace_id: str) -> tuple[int, int]:
        """Upsert videos into videos table"""
        errors = 0
        try:
            video_data = []
            for video in videos:
                try:
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
                except Exception as e:
                    logger.warning(f"Skipping video {video.video_id}: {e}", extra={"trace_id": trace_id})
                    errors += 1
                    continue

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

            return len(video_data), errors

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to upsert videos: {e}", extra={"trace_id": trace_id})
            return 0, len(videos)

    def _insert_metrics_snapshots(self, videos: List[YouTubeVideo], trace_id: str) -> tuple[int, int]:
        """Insert metrics snapshots"""
        errors = 0
        try:
            # Round to minute for deduplication
            now = datetime.now(timezone.utc)
            captured_at = now.replace(second=0, microsecond=0)
            snapshot_data = []

            for video in videos:
                try:
                    snapshot_data.append({
                        "video_id": video.video_id,
                        "captured_at": captured_at,
                        "view_count": video.view_count,
                        "like_count": video.like_count,
                        "comment_count": video.comment_count
                    })
                except Exception as e:
                    logger.warning(f"Skipping snapshot for {video.video_id}: {e}", extra={"trace_id": trace_id})
                    errors += 1
                    continue

            self.db.bulk_insert_mappings(VideoMetricsSnapshot, snapshot_data)
            self.db.commit()

            return len(snapshot_data), errors

        except Exception as e:
            self.db.rollback()
            logger.error(f"Failed to insert metrics snapshots: {e}", extra={"trace_id": trace_id})
            return 0, len(videos)

def main():
    parser = argparse.ArgumentParser(description="Collect trending videos from YouTube")
    parser.add_argument("--country", default="KR", help="Country code (default: KR)")
    parser.add_argument("--limit", type=int, default=50, help="Max videos to collect (default: 50)")
    parser.add_argument("--dry-run", action="store_true", help="Don't write to database")

    args = parser.parse_args()

    setup_json_logging()

    with TrendingCollector() as collector:
        collector.collect_trending(args.country, args.limit, args.dry_run)

if __name__ == "__main__":
    main()