"""Tests for collection idempotency and duplicate prevention"""
import pytest
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from core.db import SessionLocal
from collection.jobs.collector_trending import TrendingCollector


class TestCollectionIdempotency:
    """Test collection operations are idempotent"""

    @pytest.fixture
    def collector(self):
        """Create collector instance"""
        return TrendingCollector()

    def test_duplicate_snapshots_prevented_by_unique_constraint(self):
        """Test that unique constraint prevents duplicate snapshots"""
        with SessionLocal() as session:
            # Try to insert duplicate snapshots manually
            captured_at = datetime.now(timezone.utc).replace(second=0, microsecond=0)

            # First create a test video
            session.execute(text("""
                INSERT INTO videos (video_id, title, country_code)
                VALUES ('test_video_1', 'Test Video', 'KR')
                ON CONFLICT (video_id) DO NOTHING
            """))
            session.commit()

            # First snapshot insert should succeed
            session.execute(text("""
                INSERT INTO video_metrics_snapshot (video_id, captured_at, view_count, like_count, comment_count)
                VALUES ('test_video_1', :captured_at, 1000, 10, 5)
            """), {"captured_at": captured_at})
            session.commit()

            # Second insert with same (video_id, captured_at) should fail
            with pytest.raises(IntegrityError):
                session.execute(text("""
                    INSERT INTO video_metrics_snapshot (video_id, captured_at, view_count, like_count, comment_count)
                    VALUES ('test_video_1', :captured_at, 1001, 11, 6)
                """), {"captured_at": captured_at})
                session.commit()

            # Cleanup
            session.rollback()
            session.execute(text("DELETE FROM video_metrics_snapshot WHERE video_id = 'test_video_1'"))
            session.execute(text("DELETE FROM videos WHERE video_id = 'test_video_1'"))
            session.commit()

    def test_collection_is_idempotent(self):
        """Test that running collection multiple times doesn't create duplicates"""
        # This would require mocking YouTube API - placeholder for now
        # TODO: Implement with mocked data
        pass

    def test_no_duplicate_snapshots_in_database(self):
        """Verify current database has no duplicate snapshots"""
        with SessionLocal() as session:
            result = session.execute(text("""
                SELECT video_id, captured_at, COUNT(*) as cnt
                FROM video_metrics_snapshot
                GROUP BY video_id, captured_at
                HAVING COUNT(*) > 1
            """)).fetchall()

            duplicates = [{"video_id": row.video_id, "captured_at": row.captured_at, "count": row.cnt}
                         for row in result]

            assert len(duplicates) == 0, f"Found duplicate snapshots: {duplicates}"

    def test_unique_index_exists(self):
        """Verify unique index on (video_id, captured_at) exists"""
        with SessionLocal() as session:
            result = session.execute(text("""
                SELECT indexname, indexdef
                FROM pg_indexes
                WHERE tablename = 'video_metrics_snapshot'
                AND indexdef LIKE '%UNIQUE%'
                AND indexdef LIKE '%video_id%'
                AND indexdef LIKE '%captured_at%'
            """)).fetchall()

            assert len(result) > 0, "Unique index on (video_id, captured_at) not found"
            index_names = [row.indexname for row in result]
            assert 'idx_video_metrics_video_captured_unique' in index_names


if __name__ == "__main__":
    pytest.main([__file__, "-v"])