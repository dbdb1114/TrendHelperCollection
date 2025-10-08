#!/usr/bin/env python3
import sys
import logging
import argparse
import json
from datetime import datetime, timezone
from typing import List, Dict, Any
import pandas as pd
import numpy as np

from sqlalchemy import text
from sqlalchemy.orm import Session

# Add project root to path
sys.path.insert(0, ".")

from core.db import SessionLocal
from core.logging import setup_json_logging

logger = logging.getLogger(__name__)

class VelocityAnalyzer:
    def __init__(self):
        self.db = SessionLocal()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.db.close()

    def analyze_velocity(self, window_hours: int = 3, top_n: int = 10) -> List[Dict[str, Any]]:
        """Calculate velocity (views per minute) for trending videos"""
        trace_id = f"velocity_analysis_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}"

        try:
            logger.info("Starting velocity analysis", extra={
                "trace_id": trace_id,
                "job": "analyzer_velocity",
                "window_hours": window_hours,
                "top_n": top_n
            })

            # Fetch metrics data
            metrics_df = self._fetch_metrics_data(window_hours, trace_id)

            if metrics_df.empty:
                logger.warning("No metrics data found", extra={"trace_id": trace_id})
                return []

            # Calculate velocity
            velocity_df = self._calculate_velocity(metrics_df, trace_id)

            # Get top N results
            top_results = self._get_top_results(velocity_df, top_n, trace_id)

            logger.info(f"Velocity analysis completed", extra={
                "trace_id": trace_id,
                "job": "analyzer_velocity",
                "window_hours": window_hours,
                "total_videos": len(velocity_df),
                "top_results": len(top_results)
            })

            return top_results

        except Exception as e:
            logger.error(f"Velocity analysis failed: {e}", extra={
                "trace_id": trace_id,
                "job": "analyzer_velocity"
            })
            raise

    def _fetch_metrics_data(self, window_hours: int, trace_id: str) -> pd.DataFrame:
        """Fetch metrics snapshots within time window"""
        try:
            query = text("""
                SELECT
                    vms.video_id,
                    vms.captured_at,
                    vms.view_count,
                    v.title,
                    v.channel
                FROM video_metrics_snapshot vms
                JOIN videos v ON vms.video_id = v.video_id
                WHERE vms.captured_at >= NOW() - INTERVAL '%s hours'
                ORDER BY vms.video_id, vms.captured_at
            """ % window_hours)

            result = self.db.execute(query)
            data = result.fetchall()

            if not data:
                return pd.DataFrame()

            df = pd.DataFrame(data, columns=['video_id', 'captured_at', 'view_count', 'title', 'channel'])
            df['captured_at'] = pd.to_datetime(df['captured_at'])

            logger.info(f"Fetched metrics data", extra={
                "trace_id": trace_id,
                "rows": len(df),
                "unique_videos": df['video_id'].nunique()
            })

            return df

        except Exception as e:
            logger.error(f"Failed to fetch metrics data: {e}", extra={"trace_id": trace_id})
            raise

    def _calculate_velocity(self, df: pd.DataFrame, trace_id: str) -> pd.DataFrame:
        """Calculate views per minute for each video"""
        try:
            velocity_results = []

            for video_id, group in df.groupby('video_id'):
                if len(group) < 2:
                    continue  # Need at least 2 data points

                # Sort by time and calculate differences
                group_sorted = group.sort_values('captured_at')

                # Calculate time differences in minutes
                time_diffs = group_sorted['captured_at'].diff()
                time_diffs_minutes = time_diffs.dt.total_seconds() / 60

                # Calculate view differences
                view_diffs = group_sorted['view_count'].diff()

                # Calculate velocity (views per minute)
                valid_mask = (time_diffs_minutes > 0) & (view_diffs >= 0)

                if not valid_mask.any():
                    continue

                velocities = view_diffs[valid_mask] / time_diffs_minutes[valid_mask]

                # Remove infinite and NaN values
                velocities = velocities[np.isfinite(velocities)]

                if len(velocities) == 0:
                    continue

                # Use maximum velocity for this video
                max_velocity = velocities.max()

                velocity_results.append({
                    'video_id': video_id,
                    'title': group['title'].iloc[0],
                    'channel': group['channel'].iloc[0],
                    'views_per_min': float(max_velocity),
                    'data_points': len(group),
                    'valid_intervals': len(velocities)
                })

            velocity_df = pd.DataFrame(velocity_results)

            if not velocity_df.empty:
                # Clip outliers (top 1%)
                velocity_df = self._clip_outliers(velocity_df, trace_id)

            return velocity_df

        except Exception as e:
            logger.error(f"Failed to calculate velocity: {e}", extra={"trace_id": trace_id})
            raise

    def _clip_outliers(self, df: pd.DataFrame, trace_id: str) -> pd.DataFrame:
        """Clip top 1% outliers by capping values at 99th percentile"""
        try:
            original_count = len(df)
            percentile_99 = df['views_per_min'].quantile(0.99)

            df_clipped = df.copy()
            df_clipped['views_per_min'] = df_clipped['views_per_min'].clip(upper=percentile_99)

            logger.info(f"Outlier clipping applied", extra={
                "trace_id": trace_id,
                "original_count": original_count,
                "values_clipped": (df['views_per_min'] > percentile_99).sum(),
                "percentile_99_threshold": float(percentile_99)
            })

            return df_clipped

        except Exception as e:
            logger.error(f"Failed to clip outliers: {e}", extra={"trace_id": trace_id})
            return df

    def _get_top_results(self, df: pd.DataFrame, top_n: int, trace_id: str) -> List[Dict[str, Any]]:
        """Get top N results sorted by velocity"""
        try:
            if df.empty:
                return []

            top_df = df.nlargest(top_n, 'views_per_min')

            results = []
            for _, row in top_df.iterrows():
                results.append({
                    "video_id": row['video_id'],
                    "title": row['title'],
                    "channel": row['channel'],
                    "views_per_min": row['views_per_min'],
                    "data_points": row['data_points'],
                    "valid_intervals": row['valid_intervals']
                })

            return results

        except Exception as e:
            logger.error(f"Failed to get top results: {e}", extra={"trace_id": trace_id})
            raise

def main():
    parser = argparse.ArgumentParser(description="Analyze velocity of trending videos")
    parser.add_argument("--window", type=int, default=3, help="Time window in hours (default: 3)")
    parser.add_argument("--top-n", type=int, default=10, help="Top N results (default: 10)")
    parser.add_argument("--out-file", help="Output file path (optional)")

    args = parser.parse_args()

    setup_json_logging()

    with VelocityAnalyzer() as analyzer:
        results = analyzer.analyze_velocity(args.window, args.top_n)

        output_data = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analysis_params": {
                "window_hours": args.window,
                "top_n": args.top_n
            },
            "results": results
        }

        # Output results
        json_output = json.dumps(output_data, indent=2, ensure_ascii=False)

        if args.out_file:
            with open(args.out_file, 'w', encoding='utf-8') as f:
                f.write(json_output)
            print(f"Results saved to {args.out_file}")
        else:
            print(json_output)

if __name__ == "__main__":
    main()