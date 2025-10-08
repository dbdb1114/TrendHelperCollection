"""Unit tests for velocity analysis edge cases and boundary conditions"""
import pytest
import pandas as pd
import numpy as np
from datetime import datetime, timezone


class TestVelocityCalculation:
    """Test velocity calculation edge cases and boundary conditions"""

    def test_normal_velocity_calculation(self, sample_velocity_data):
        """Test normal velocity calculation"""
        # Filter normal case
        df = sample_velocity_data[sample_velocity_data['video_id'] == 'v1'].copy()
        df = df.sort_values(['video_id', 'captured_at'])

        # Calculate delta time in minutes
        df['time_diff'] = df.groupby('video_id')['captured_at'].diff()
        df['time_diff_minutes'] = df['time_diff'].dt.total_seconds() / 60

        # Calculate view delta
        df['view_diff'] = df.groupby('video_id')['view_count'].diff()

        # Calculate velocity
        df['views_per_min'] = df['view_diff'] / df['time_diff_minutes']

        # Remove NaN (first row)
        valid_rows = df.dropna()

        assert len(valid_rows) == 2
        assert valid_rows.iloc[0]['views_per_min'] == 100.0  # (1100-1000)/1
        assert valid_rows.iloc[1]['views_per_min'] == 150.0  # (1250-1100)/1

    def test_zero_time_delta_filtering(self, sample_velocity_data):
        """Test that Δt=0 cases are properly filtered"""
        # Filter case with same timestamp
        df = sample_velocity_data[sample_velocity_data['video_id'] == 'v2'].copy()
        df = df.sort_values(['video_id', 'captured_at'])

        # Calculate time difference
        df['time_diff'] = df.groupby('video_id')['captured_at'].diff()
        df['time_diff_minutes'] = df['time_diff'].dt.total_seconds() / 60

        # Filter out zero or negative time deltas
        valid_df = df[df['time_diff_minutes'] > 0]

        assert len(valid_df) == 0, "Should filter out Δt=0 cases"

    def test_negative_view_delta_filtering(self, sample_velocity_data):
        """Test that negative view deltas are filtered"""
        # Filter case with view decrease
        df = sample_velocity_data[sample_velocity_data['video_id'] == 'v3'].copy()
        df = df.sort_values(['video_id', 'captured_at'])

        # Calculate deltas
        df['time_diff'] = df.groupby('video_id')['captured_at'].diff()
        df['time_diff_minutes'] = df['time_diff'].dt.total_seconds() / 60
        df['view_diff'] = df.groupby('video_id')['view_count'].diff()
        df['views_per_min'] = df['view_diff'] / df['time_diff_minutes']

        # Filter negative velocities
        valid_df = df[(df['time_diff_minutes'] > 0) & (df['views_per_min'] >= 0)]

        assert len(valid_df) == 0, "Should filter out negative view deltas"

    def test_outlier_clipping(self, sample_velocity_data):
        """Test 99th percentile outlier clipping"""
        # Create dataset with clear outlier
        df = sample_velocity_data.copy()
        df = df.sort_values(['video_id', 'captured_at'])

        # Calculate velocity for all valid cases
        df['time_diff'] = df.groupby('video_id')['captured_at'].diff()
        df['time_diff_minutes'] = df['time_diff'].dt.total_seconds() / 60
        df['view_diff'] = df.groupby('video_id')['view_count'].diff()
        df['views_per_min'] = df['view_diff'] / df['time_diff_minutes']

        # Remove invalid cases
        valid_df = df[(df['time_diff_minutes'] > 0) & (df['views_per_min'] >= 0)].copy()

        if len(valid_df) > 0:
            # Apply 99th percentile clipping
            p99 = np.percentile(valid_df['views_per_min'], 99)
            valid_df['views_per_min_clipped'] = np.clip(valid_df['views_per_min'], 0, p99)

            # Verify clipping applied
            assert valid_df['views_per_min_clipped'].max() <= p99

    def test_nan_infinity_handling(self):
        """Test handling of NaN and infinity values"""
        # Create problematic data
        test_data = pd.DataFrame([
            {"video_id": "test", "time_diff_minutes": 0, "view_diff": 100},  # Division by zero
            {"video_id": "test", "time_diff_minutes": 1, "view_diff": np.nan},  # NaN view diff
            {"video_id": "test", "time_diff_minutes": np.nan, "view_diff": 100},  # NaN time diff
        ])

        # Calculate velocity
        test_data['views_per_min'] = test_data['view_diff'] / test_data['time_diff_minutes']

        # Filter out problematic values
        clean_data = test_data[
            (test_data['time_diff_minutes'] > 0) &
            np.isfinite(test_data['views_per_min']) &
            (test_data['views_per_min'] >= 0)
        ]

        assert len(clean_data) == 0, "Should filter out all problematic cases"

    def test_empty_dataset_handling(self):
        """Test handling of empty datasets"""
        empty_df = pd.DataFrame(columns=['video_id', 'captured_at', 'view_count'])

        # Should not crash on empty data
        result = empty_df.groupby('video_id')['captured_at'].diff()
        assert len(result) == 0

    def test_single_snapshot_per_video(self):
        """Test handling when videos have only single snapshots"""
        single_snapshot_data = pd.DataFrame([
            {"video_id": "v1", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 1000},
            {"video_id": "v2", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 2000},
        ])

        # Calculate time differences - should result in NaN for all
        single_snapshot_data['time_diff'] = single_snapshot_data.groupby('video_id')['captured_at'].diff()

        # All time diffs should be NaN (no previous snapshot)
        assert single_snapshot_data['time_diff'].isna().all()

    def test_velocity_calculation_boundary_values(self):
        """Test velocity calculation with boundary values"""
        boundary_data = pd.DataFrame([
            # Very small time difference (1 second)
            {"video_id": "v1", "captured_at": datetime(2025, 1, 1, 10, 0, 0, tzinfo=timezone.utc), "view_count": 1000},
            {"video_id": "v1", "captured_at": datetime(2025, 1, 1, 10, 0, 1, tzinfo=timezone.utc), "view_count": 1001},

            # Very large view difference
            {"video_id": "v2", "captured_at": datetime(2025, 1, 1, 10, 0, tzinfo=timezone.utc), "view_count": 0},
            {"video_id": "v2", "captured_at": datetime(2025, 1, 1, 10, 1, tzinfo=timezone.utc), "view_count": 1000000},
        ])

        df = boundary_data.sort_values(['video_id', 'captured_at'])
        df['time_diff'] = df.groupby('video_id')['captured_at'].diff()
        df['time_diff_minutes'] = df['time_diff'].dt.total_seconds() / 60
        df['view_diff'] = df.groupby('video_id')['view_count'].diff()
        df['views_per_min'] = df['view_diff'] / df['time_diff_minutes']

        valid_df = df[(df['time_diff_minutes'] > 0) & (df['views_per_min'] >= 0)]

        # Should handle extreme but valid values
        assert len(valid_df) == 2
        assert all(np.isfinite(valid_df['views_per_min']))
        assert all(valid_df['views_per_min'] >= 0)